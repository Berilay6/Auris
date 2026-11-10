"""Download the pilot region's drive network from OpenStreetMap with OSMnx and save it as raw .osm.

All region-specific values (boundary, OSM snapshot date, tags, output name) are read
from `config/pilot_region.yaml`; this module contains no hard-coded coordinates.

Usage (from the backend/ directory):

    python -m auris.cli.bootstrap_network            # default config
    python -m auris.cli.bootstrap_network --force    # overwrite the existing output
    python -m auris.cli.bootstrap_network --config ../config/pilot_region.yaml --output-dir D:/shared/auris-data

Reproducibility:
  * The Overpass query is pinned to the OSM state at `osm.snapshot_date`.
  * OSMnx's XML output (run-time timestamps + set-order-dependent tag/attribute order)
    is normalized; the same config + same OSMnx version yields a byte-identical file.
  * A `<file>.meta.json` containing the SHA-256 is written next to it.

Note: in S2 the logic moves to `auris.network.bootstrap`; this file stays a thin CLI.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib.metadata import version as pkg_version
from pathlib import Path
from typing import Any

import yaml

log = logging.getLogger("auris.bootstrap_network")

# backend/auris/cli/bootstrap_network.py -> repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = REPO_ROOT / "config" / "pilot_region.yaml"
DEFAULT_DATA_DIR = REPO_ROOT / "auris-data"


class ConfigError(ValueError):
    """pilot_region.yaml is invalid."""


@dataclass(frozen=True)
class RegionConfig:
    region_id: str
    name: str
    boundary_type: str  # "polygon" | "bbox"
    polygon: list[tuple[float, float]] | None
    bbox: tuple[float, float, float, float] | None  # (west, south, east, north)
    buffer_m: float
    network_type: str
    snapshot_date: str
    truncate_by_edge: bool
    extra_way_tags: list[str]
    extra_node_tags: list[str]
    output_dir: str
    output_filename: str


# --------------------------------------------------------------------------- config


def _require(mapping: dict[str, Any], key: str, where: str) -> Any:
    if not isinstance(mapping, dict) or key not in mapping or mapping[key] is None:
        raise ConfigError(f"missing field '{where}.{key}'")
    return mapping[key]


def _check_lon_lat(lon: float, lat: float, where: str) -> None:
    if not (-180 <= lon <= 180 and -90 <= lat <= 90):
        raise ConfigError(f"{where}: invalid coordinate [lon={lon}, lat={lat}] (order must be [longitude, latitude])")


def load_config(path: Path) -> RegionConfig:
    if not path.is_file():
        raise ConfigError(f"config not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    region = _require(raw, "region", "")
    boundary = _require(region, "boundary", "region")
    osm = _require(raw, "osm", "")
    output = _require(raw, "output", "")

    btype = _require(boundary, "type", "region.boundary")
    polygon = bbox = None
    if btype == "polygon":
        pts = _require(boundary, "polygon", "region.boundary")
        if not isinstance(pts, list) or len(pts) < 4:
            raise ConfigError("region.boundary.polygon must be a closed ring of at least 4 points")
        polygon = []
        for i, p in enumerate(pts):
            if not (isinstance(p, list) and len(p) == 2):
                raise ConfigError(f"region.boundary.polygon[{i}] must be of the form [lon, lat]")
            lon, lat = float(p[0]), float(p[1])
            _check_lon_lat(lon, lat, f"region.boundary.polygon[{i}]")
            polygon.append((lon, lat))
        if polygon[0] != polygon[-1]:
            raise ConfigError("region.boundary.polygon is not closed: first and last points must be equal")
    elif btype == "bbox":
        b = _require(boundary, "bbox", "region.boundary")
        west, south, east, north = (float(_require(b, k, "region.boundary.bbox")) for k in ("west", "south", "east", "north"))
        _check_lon_lat(west, south, "region.boundary.bbox")
        _check_lon_lat(east, north, "region.boundary.bbox")
        if not (west < east and south < north):
            raise ConfigError("region.boundary.bbox: requires west < east and south < north")
        bbox = (west, south, east, north)
    else:
        raise ConfigError(f"region.boundary.type must be 'polygon' or 'bbox', got '{btype}'")

    buffer_m = float(boundary.get("buffer_m") or 0)
    if buffer_m < 0:
        raise ConfigError("region.boundary.buffer_m must not be negative")

    snapshot = str(_require(osm, "snapshot_date", "osm"))
    try:
        datetime.strptime(snapshot, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ConfigError(f"osm.snapshot_date must be formatted as 'YYYY-MM-DDTHH:MM:SSZ': {snapshot!r}") from exc

    region_id = str(_require(region, "id", "region"))
    if not region_id.replace("_", "").replace("-", "").isalnum():
        raise ConfigError(f"region.id may only contain letters, digits, '_' and '-': {region_id!r}")

    return RegionConfig(
        region_id=region_id,
        name=str(region.get("name", "")),
        boundary_type=btype,
        polygon=polygon,
        bbox=bbox,
        buffer_m=buffer_m,
        network_type=str(_require(osm, "network_type", "osm")),
        snapshot_date=snapshot,
        truncate_by_edge=bool(osm.get("truncate_by_edge", True)),
        extra_way_tags=[str(t) for t in osm.get("extra_way_tags") or []],
        extra_node_tags=[str(t) for t in osm.get("extra_node_tags") or []],
        output_dir=str(_require(output, "dir", "output")),
        output_filename=str(output.get("filename") or f"{region_id}.osm"),
    )


def resolve_data_dir(cli_value: str | None) -> Path:
    """Precedence: --output-dir > AURIS_DATA_DIR > <repo>/auris-data. Relative paths resolve against the repo root."""
    value = cli_value or os.environ.get("AURIS_DATA_DIR")
    if not value:
        return DEFAULT_DATA_DIR
    p = Path(value)
    return p if p.is_absolute() else (REPO_ROOT / p).resolve()


# --------------------------------------------------------------------------- download


def configure_osmnx(cfg: RegionConfig, cache_dir: Path, use_cache: bool) -> None:
    import osmnx as ox

    # Required by save_graph_xml: each way is kept as a single edge in its OSM direction
    ox.settings.all_oneway = True
    ox.settings.useful_tags_way = sorted(set(ox.settings.useful_tags_way) | set(cfg.extra_way_tags))
    ox.settings.useful_tags_node = sorted(set(ox.settings.useful_tags_node) | set(cfg.extra_node_tags))
    # Pin Overpass to the OSM state at a fixed date
    ox.settings.overpass_settings = '[out:json][timeout:{timeout}]{maxsize}[date:"' + cfg.snapshot_date + '"]'
    ox.settings.use_cache = use_cache
    ox.settings.cache_folder = str(cache_dir)
    ox.settings.log_console = False


def build_boundary(cfg: RegionConfig):
    """Convert the configured boundary (polygon or bbox) to a WGS84 shapely polygon, applying the buffer if set."""
    import osmnx as ox
    from shapely.geometry import Polygon, box

    poly = Polygon(cfg.polygon) if cfg.boundary_type == "polygon" else box(*cfg.bbox)
    if not poly.is_valid:
        raise ConfigError("region.boundary is invalid (the polygon may self-intersect)")
    if cfg.buffer_m > 0:
        # Project to local UTM so the buffer is in meters, then project back to WGS84
        projected, crs = ox.projection.project_geometry(poly)
        poly, _ = ox.projection.project_geometry(projected.buffer(cfg.buffer_m, join_style="mitre"), crs=crs, to_latlong=True)
    return poly


def download_graph(cfg: RegionConfig):
    import osmnx as ox

    return ox.graph_from_polygon(
        build_boundary(cfg),
        network_type=cfg.network_type,
        simplify=False,  # writing .osm requires an unsimplified graph; netconvert also prefers raw geometry
        retain_all=False,
        truncate_by_edge=cfg.truncate_by_edge,
    )


# --------------------------------------------------------------------------- write


def normalize_osm_xml(path: Path, timestamp: str) -> None:
    """Make OSMnx's output deterministic.

    OSMnx stamps every element with the current run time, and its tag/attribute
    order depends on Python set iteration order (hash seed). This sets every
    timestamp to the snapshot date and sorts attributes and <tag> elements by key.
    """
    tree = ET.parse(path)
    root = tree.getroot()
    for el in root.iter():
        if "timestamp" in el.attrib:
            el.set("timestamp", timestamp)
        el.attrib = dict(sorted(el.attrib.items()))
    for el in root:
        if el.tag in ("node", "way"):
            tags = [c for c in el if c.tag == "tag"]
            others = [c for c in el if c.tag != "tag"]
            el[:] = others + sorted(tags, key=lambda t: t.get("k", ""))
    ET.indent(tree, space="  ")
    tree.write(path, encoding="utf-8", xml_declaration=True)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_outputs(G, cfg: RegionConfig, config_path: Path, out_path: Path) -> dict[str, Any]:
    import osmnx as ox

    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_name(out_path.name + ".tmp")
    try:
        ox.io.save_graph_xml(G, filepath=tmp)
        normalize_osm_xml(tmp, cfg.snapshot_date)
        os.replace(tmp, out_path)  # atomic, so a half-written file is never left behind
    finally:
        tmp.unlink(missing_ok=True)

    meta = {
        "region_id": cfg.region_id,
        "region_name": cfg.name,
        "file": out_path.name,
        "sha256": sha256_of(out_path),
        "size_bytes": out_path.stat().st_size,
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "boundary": {"type": cfg.boundary_type, "polygon": cfg.polygon, "bbox": cfg.bbox, "buffer_m": cfg.buffer_m},
        "network_type": cfg.network_type,
        "osm_snapshot_date": cfg.snapshot_date,
        "config_sha256": sha256_of(config_path),
        "osmnx_version": pkg_version("osmnx"),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "attribution": "© OpenStreetMap contributors, ODbL 1.0 (https://www.openstreetmap.org/copyright)",
    }
    meta_path = out_path.with_name(out_path.name + ".meta.json")
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return meta


# --------------------------------------------------------------------------- cli


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="python -m auris.cli.bootstrap_network",
        description="Download the pilot region's drive network from OSM and save it as .osm.",
    )
    p.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help=f"region config (default: {DEFAULT_CONFIG})")
    p.add_argument("--output-dir", help="data root directory (default: $AURIS_DATA_DIR or <repo>/auris-data)")
    p.add_argument("--force", action="store_true", help="overwrite the existing output")
    p.add_argument("--no-cache", action="store_true", help="bypass the OSMnx HTTP cache (re-fetch from Overpass)")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(message)s")

    try:
        cfg = load_config(args.config)
    except ConfigError as exc:
        log.error("Config error: %s", exc)
        return 2

    data_dir = resolve_data_dir(args.output_dir)
    out_path = data_dir / cfg.output_dir / cfg.output_filename
    if out_path.exists() and not args.force:
        log.error("%s already exists. Use --force to download again.", out_path)
        return 1

    log.info("Region: %s (%s), boundary=%s, OSM date=%s", cfg.region_id, cfg.name, cfg.boundary_type, cfg.snapshot_date)
    configure_osmnx(cfg, cache_dir=data_dir / ".cache" / "osmnx", use_cache=not args.no_cache)

    try:
        G = download_graph(cfg)
    except ConfigError as exc:
        log.error("Config error: %s", exc)
        return 2
    except Exception as exc:  # network / Overpass errors
        log.error("Download failed: %s", exc)
        return 3

    log.info("Graph downloaded: %d nodes, %d edges", G.number_of_nodes(), G.number_of_edges())
    meta = write_outputs(G, cfg, args.config.resolve(), out_path)
    log.info("Wrote: %s (%d bytes, sha256=%s)", out_path, meta["size_bytes"], meta["sha256"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
