"""Immutable base network builder (SCRUM-6, HLD MK2).

Generates `auris-data/base_network/base.net.xml` from `midtown_east.osm` using
`config/sumo/netconvert.netccfg`, normalizes the generated timestamp for byte-level
reproducibility, inspects the resulting SUMO topology, and writes a sibling
`base.net.xml.meta.json` manifest with SHA-256 checksums and quality metrics.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from auris.sumo.cli import find_sumo_binary, get_binary_version, run_netconvert

# Matches SUMO's runtime timestamp comment:
#   <!-- generated on 2026-11-19 15:40:00 by Eclipse SUMO netconvert 1.28.0
_GENERATED_ON_RE = re.compile(r"(<!-- generated on )([^b]+?)( by Eclipse SUMO)")
# Matches absolute file paths that SUMO embeds inside the header comment
_OSM_ATTR_RE = re.compile(r'(<osm-files value=")([^"]+)("/>)')
_OUT_ATTR_RE = re.compile(r'(<output-file value=")([^"]+)("/>)')


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_net_xml_header(path: Path, *, snapshot_date: str, osm_name: str, out_name: str) -> None:
    """Replace non-deterministic timestamp and machine-specific paths in the header comment."""
    text = path.read_text(encoding="utf-8")
    text = _GENERATED_ON_RE.sub(rf"\g<1>{snapshot_date}\g<3>", text, count=1)
    text = _OSM_ATTR_RE.sub(rf"\g<1>{osm_name}\g<3>", text, count=1)
    text = _OUT_ATTR_RE.sub(rf"\g<1>{out_name}\g<3>", text, count=1)
    path.write_text(text, encoding="utf-8")


def _tarjan_scc_sizes(nodes: set[str], adj: dict[str, set[str]]) -> list[int]:
    """Compute strongly connected component sizes without external graph dependencies."""
    index_counter = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    indices: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    sizes: list[int] = []

    # Iterative Tarjan to avoid recursion limit issues on larger networks
    for start in sorted(nodes):
        if start in indices:
            continue
        call_stack: list[tuple[str, list[str], int]] = [(start, sorted(adj.get(start, ())), 0)]
        indices[start] = lowlink[start] = index_counter
        index_counter += 1
        stack.append(start)
        on_stack.add(start)

        while call_stack:
            v, nbrs, i = call_stack[-1]
            if i < len(nbrs):
                call_stack[-1] = (v, nbrs, i + 1)
                w = nbrs[i]
                if w not in indices:
                    indices[w] = lowlink[w] = index_counter
                    index_counter += 1
                    stack.append(w)
                    on_stack.add(w)
                    call_stack.append((w, sorted(adj.get(w, ())), 0))
                elif w in on_stack:
                    lowlink[v] = min(lowlink[v], indices[w])
            else:
                call_stack.pop()
                if call_stack:
                    parent = call_stack[-1][0]
                    lowlink[parent] = min(lowlink[parent], lowlink[v])
                if lowlink[v] == indices[v]:
                    comp_size = 0
                    while True:
                        w = stack.pop()
                        on_stack.remove(w)
                        comp_size += 1
                        if w == v:
                            break
                    sizes.append(comp_size)

    return sorted(sizes, reverse=True)


def _weakly_connected_components(nodes: set[str], adj: dict[str, set[str]]) -> int:
    undirected: dict[str, set[str]] = defaultdict(set)
    for u, nbrs in adj.items():
        for v in nbrs:
            undirected[u].add(v)
            undirected[v].add(u)
    seen: set[str] = set()
    count = 0
    for start in nodes:
        if start in seen:
            continue
        count += 1
        queue = [start]
        seen.add(start)
        while queue:
            cur = queue.pop()
            for nxt in undirected.get(cur, ()):
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
    return count


def inspect_net_xml(net_path: Path) -> dict[str, Any]:
    """Extract segment, junction, traffic-light, connectivity, and direction statistics."""
    tree = ET.parse(net_path)
    root = tree.getroot()

    location = root.find("location")
    loc_attrib = location.attrib if location is not None else {}

    junction_coords: dict[str, tuple[float, float]] = {}
    junction_types: Counter[str] = Counter()
    dead_end_ids: list[str] = []
    internal_junctions = 0

    for j in root.findall("junction"):
        jtype = j.get("type", "")
        jid = j.get("id", "")
        if jtype == "internal":
            internal_junctions += 1
            continue
        junction_types[jtype] += 1
        junction_coords[jid] = (float(j.get("x", "0")), float(j.get("y", "0")))
        if jtype == "dead_end":
            dead_end_ids.append(jid)

    normal_edges = 0
    internal_edges = 0
    total_lanes = 0
    total_length_m = 0.0
    street_edge_counts: Counter[str] = Counter()
    highway_type_counts: Counter[str] = Counter()
    adj: dict[str, set[str]] = defaultdict(set)
    edge_nodes: set[str] = set()
    avenue_directions: dict[str, Counter[str]] = {
        "Lexington Avenue": Counter(),
        "3rd Avenue": Counter(),
        "Park Avenue": Counter(),
    }

    for e in root.findall("edge"):
        if e.get("function") == "internal":
            internal_edges += 1
            continue
        normal_edges += 1
        lanes = e.findall("lane")
        total_lanes += len(lanes)
        if lanes:
            total_length_m += float(lanes[0].get("length", "0"))
        name = e.get("name", "") or "(unnamed)"
        street_edge_counts[name] += 1
        etype = e.get("type", "") or "(untyped)"
        highway_type_counts[etype] += 1

        u = e.get("from", "")
        v = e.get("to", "")
        if u and v:
            adj[u].add(v)
            edge_nodes.add(u)
            edge_nodes.add(v)
            if name in avenue_directions and u in junction_coords and v in junction_coords:
                y0 = junction_coords[u][1]
                y1 = junction_coords[v][1]
                avenue_directions[name]["northbound" if y1 > y0 else "southbound"] += 1

    tl_logic_count = len(root.findall("tlLogic"))
    wcc = _weakly_connected_components(edge_nodes, adj)
    scc_sizes = _tarjan_scc_sizes(edge_nodes, adj)
    main_scc = scc_sizes[0] if scc_sizes else 0

    return {
        "total_edges": normal_edges,
        "internal_edges": internal_edges,
        "total_lanes": total_lanes,
        "total_length_m": round(total_length_m, 2),
        "total_length_km": round(total_length_m / 1000.0, 3),
        "total_junctions": sum(junction_types.values()),
        "internal_junctions": internal_junctions,
        "traffic_light_junctions": junction_types.get("traffic_light", 0),
        "tl_logic_count": tl_logic_count,
        "priority_junctions": junction_types.get("priority", 0),
        "dead_end_junctions": len(dead_end_ids),
        "dead_end_ids": sorted(dead_end_ids),
        "weakly_connected_components": wcc,
        "strongly_connected_component_sizes": scc_sizes,
        "main_scc_ratio": round(main_scc / len(edge_nodes), 3) if edge_nodes else 0.0,
        "proj_parameter": loc_attrib.get("projParameter", ""),
        "net_offset": loc_attrib.get("netOffset", ""),
        "conv_boundary": loc_attrib.get("convBoundary", ""),
        "orig_boundary": loc_attrib.get("origBoundary", ""),
        "highway_type_counts": dict(sorted(highway_type_counts.items())),
        "street_edge_counts": dict(sorted(street_edge_counts.items())),
        "avenue_directions": {k: dict(v) for k, v in avenue_directions.items() if v},
    }


def _read_snapshot_date(osm_path: Path) -> str:
    meta_path = osm_path.with_name(osm_path.name + ".meta.json")
    if meta_path.is_file():
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        if data.get("osm_snapshot_date"):
            return str(data["osm_snapshot_date"])
    return "2026-10-01T00:00:00Z"


def build_base_network(
    *,
    osm_path: Path,
    netccfg_path: Path,
    out_path: Path,
    pilot_config_path: Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Run netconvert atomically, verify topology, and write `base.net.xml` + `.meta.json`."""
    if not osm_path.is_file():
        raise FileNotFoundError(f"Source OSM file not found: {osm_path}")
    if not netccfg_path.is_file():
        raise FileNotFoundError(f"netconvert config not found: {netccfg_path}")
    if out_path.exists() and not force:
        raise FileExistsError(f"{out_path} already exists. Pass --force to overwrite.")

    netconvert_bin = find_sumo_binary("netconvert")
    netconvert_version = get_binary_version(netconvert_bin)
    snapshot_date = _read_snapshot_date(osm_path)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_name(out_path.name + ".tmp")

    try:
        res = run_netconvert(netccfg_path, osm_file=osm_path, output_file=tmp_path)
        normalize_net_xml_header(
            tmp_path,
            snapshot_date=snapshot_date,
            osm_name=osm_path.name,
            out_name=out_path.name,
        )
        os.replace(tmp_path, out_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    warnings = [line.strip() for line in res.stderr.splitlines() if "Warning:" in line]
    topology = inspect_net_xml(out_path)
    topology["warnings"] = warnings

    meta: dict[str, Any] = {
        "file": out_path.name,
        "sha256": sha256_of(out_path),
        "size_bytes": out_path.stat().st_size,
        "source_osm_file": osm_path.name,
        "source_osm_sha256": sha256_of(osm_path),
        "netccfg_file": netccfg_path.name,
        "netccfg_sha256": sha256_of(netccfg_path),
        "pilot_region_config_sha256": sha256_of(pilot_config_path) if pilot_config_path and pilot_config_path.is_file() else None,
        "netconvert_version": netconvert_version,
        "topology": topology,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    meta_path = out_path.with_name(out_path.name + ".meta.json")
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return meta
