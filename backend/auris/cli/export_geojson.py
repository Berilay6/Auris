"""Export SUMO `base.net.xml` as a WGS84 GeoJSON file for the frontend (SCRUM-19).

Usage (from the backend/ directory):

    python -m auris.cli.export_geojson
    python -m auris.cli.export_geojson --input ../auris-data/base_network/base.net.xml --output ../frontend/public/network.geojson
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from auris.network.geojson_exporter import export_network_geojson

log = logging.getLogger("auris.export_geojson")

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA_DIR = REPO_ROOT / "auris-data"
DEFAULT_OUTPUT = REPO_ROOT / "frontend" / "public" / "network.geojson"


def resolve_data_dir() -> Path:
    value = os.environ.get("AURIS_DATA_DIR")
    if not value:
        return DEFAULT_DATA_DIR
    p = Path(value)
    return p if p.is_absolute() else (REPO_ROOT / p).resolve()


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="python -m auris.cli.export_geojson",
        description="Convert SUMO base.net.xml into a WGS84 GeoJSON FeatureCollection.",
    )
    p.add_argument(
        "--input",
        type=Path,
        default=resolve_data_dir() / "base_network" / "base.net.xml",
        help="input SUMO .net.xml file (default: <data-dir>/base_network/base.net.xml)",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"output GeoJSON path (default: {DEFAULT_OUTPUT})",
    )
    p.add_argument(
        "--no-junctions",
        action="store_true",
        help="use raw edge shapes without extending to junction centers",
    )
    p.add_argument(
        "--precision",
        type=int,
        default=6,
        help="decimal precision for WGS84 coordinates (default: 6)",
    )
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    try:
        geojson = export_network_geojson(
            args.input.resolve(),
            args.output.resolve(),
            include_junctions=not args.no_junctions,
            precision=args.precision,
        )
    except FileNotFoundError as exc:
        log.error("%s", exc)
        return 2

    out_path = args.output.resolve()
    log.info(
        "Wrote: %s (%d features, %d bytes)",
        out_path,
        len(geojson["features"]),
        out_path.stat().st_size,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
