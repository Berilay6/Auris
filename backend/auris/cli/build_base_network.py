"""Generate SUMO's immutable base network (`base.net.xml`) from the pilot `.osm` file (SCRUM-6).

Usage (from the backend/ directory):

    python -m auris.cli.build_base_network            # generate if missing
    python -m auris.cli.build_base_network --force    # overwrite existing base.net.xml
    python -m auris.cli.build_base_network --gui      # open the generated network in sumo-gui
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

from auris.network.bootstrap import build_base_network
from auris.storage.layout import DataLayout
from auris.sumo.cli import SumoCommandError, SumoNotFoundError, find_sumo_binary

log = logging.getLogger("auris.build_base_network")

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_NETCCFG = REPO_ROOT / "config" / "sumo" / "netconvert.netccfg"
DEFAULT_PILOT_CONFIG = REPO_ROOT / "config" / "pilot_region.yaml"
DEFAULT_TYPEMAP = REPO_ROOT / "config" / "sumo" / "osm-speeds.typ.xml"


def resolve_layout(cli_value: str | None) -> DataLayout:
    if cli_value:
        p = Path(cli_value)
        return DataLayout(p if p.is_absolute() else (REPO_ROOT / p).resolve())
    return DataLayout.from_env()


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="python -m auris.cli.build_base_network",
        description="Build auris-data/base_network/base.net.xml via SUMO netconvert.",
    )
    p.add_argument("--osm", type=Path, help="input .osm file (default: <data-dir>/base_network/midtown_east.osm)")
    p.add_argument("--netccfg", type=Path, default=DEFAULT_NETCCFG, help=f"netconvert config (default: {DEFAULT_NETCCFG})")
    p.add_argument("--pilot-config", type=Path, default=DEFAULT_PILOT_CONFIG, help=f"pilot region config (default: {DEFAULT_PILOT_CONFIG})")
    p.add_argument("--typemap", type=Path, default=DEFAULT_TYPEMAP, help=f"OSM speed typemap override (default: {DEFAULT_TYPEMAP})")
    p.add_argument("--no-typemap", action="store_true", help="do not apply custom speed typemap override")
    p.add_argument("--output-dir", help="data root directory (default: DataLayout.from_env())")
    p.add_argument("--output", type=Path, help="output .net.xml path (default: <data-dir>/base_network/base.net.xml)")
    p.add_argument("--force", action="store_true", help="overwrite existing base.net.xml")
    p.add_argument("--gui", action="store_true", help="launch sumo-gui on the generated base.net.xml")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(message)s")

    layout = resolve_layout(args.output_dir)
    base_dir = layout.base_network_dir()
    osm_path = (args.osm or (base_dir / "midtown_east.osm")).resolve()
    out_path = (args.output or (base_dir / "base.net.xml")).resolve()
    netccfg_path = args.netccfg.resolve()
    pilot_config_path = args.pilot_config.resolve()
    typemap_path = None if args.no_typemap else args.typemap.resolve()

    try:
        meta = build_base_network(
            osm_path=osm_path,
            netccfg_path=netccfg_path,
            out_path=out_path,
            pilot_config_path=pilot_config_path,
            typemap_path=typemap_path,
            force=args.force,
        )
    except FileExistsError as exc:
        log.error("%s", exc)
        return 1
    except (FileNotFoundError, ValueError, SumoNotFoundError) as exc:
        log.error("%s", exc)
        return 2
    except SumoCommandError as exc:
        log.error("%s", exc)
        return 3

    topo = meta["topology"]
    log.info("Wrote: %s (%d bytes, sha256=%s)", out_path, meta["size_bytes"], meta["sha256"])
    log.info(
        "Topology: %d edges (%d lanes, %.3f km), %d junctions (%d traffic lights, %d priority, %d dead-ends)",
        topo["total_edges"],
        topo["total_lanes"],
        topo["total_length_km"],
        topo["total_junctions"],
        topo["traffic_light_junctions"],
        topo["priority_junctions"],
        topo["dead_end_junctions"],
    )
    log.info(
        "Connectivity: WCC=%d, main SCC=%d/%d (%.1f%%)",
        topo["weakly_connected_components"],
        topo["strongly_connected_component_sizes"][0] if topo["strongly_connected_component_sizes"] else 0,
        topo["total_junctions"],
        topo["main_scc_ratio"] * 100.0,
    )
    log.info("Avenue directions: %s", topo["avenue_directions"])
    if topo["warnings"]:
        log.info("netconvert warnings (%d): %s", len(topo["warnings"]), topo["warnings"][0])

    if args.gui:
        try:
            sumo_gui = find_sumo_binary("sumo-gui")
        except SumoNotFoundError as exc:
            log.error("%s", exc)
            return 2
        log.info("Launching sumo-gui: %s -n %s", sumo_gui, out_path)
        subprocess.Popen([str(sumo_gui), "-n", str(out_path)])

    return 0


if __name__ == "__main__":
    sys.exit(main())
