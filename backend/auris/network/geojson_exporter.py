"""Convert a SUMO `.net.xml` road network into WGS84 GeoJSON (SCRUM-19, HLD AS3/AS1).

In S1 this module is called by the CLI (`python -m auris.cli.export_geojson`) to write
the static `frontend/public/network.geojson`. In S2 it is imported directly by the
`GET /api/network` FastAPI endpoint without duplicating any conversion logic.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import sumolib

from auris.storage.atomic import atomic_write_text


def _is_internal_edge(edge: Any) -> bool:
    """Return True for SUMO internal/special junction edges."""
    if edge.isSpecial():
        return True
    if edge.getFunction() == "internal":
        return True
    return str(edge.getID()).startswith(":")


def _deduplicate_coords(coords: list[list[float]]) -> list[list[float]]:
    out: list[list[float]] = []
    for pt in coords:
        if not out or out[-1] != pt:
            out.append(pt)
    return out


def net_to_geojson(
    net_path: Path | str,
    *,
    include_junctions: bool = True,
    precision: int = 6,
) -> dict[str, Any]:
    """Read a SUMO `.net.xml` file via `sumolib` and return a WGS84 GeoJSON FeatureCollection.

    Each non-internal edge becomes a GeoJSON `LineString` feature with coordinates in
    RFC 7946 `[longitude, latitude]` order and properties:
      - `edgeId` (str): SUMO edge identifier
      - `lanes` (int): number of lanes on the edge
      - `speed` (float): speed limit in m/s (SUMO native unit)
      - `speedKmh` (float): speed limit in km/h (display convenience)
      - `name` (str): street name if present
      - `highway` (str): SUMO/OSM road type
      - `length` (float): edge length in meters
      - `fromNode` / `toNode` (str): start and end junction IDs
    """
    path = Path(net_path)
    if not path.is_file():
        raise FileNotFoundError(f"SUMO network file not found: {path}")

    net = sumolib.net.readNet(str(path), withInternal=False)
    features: list[dict[str, Any]] = []

    edges = sorted(net.getEdges(), key=lambda e: str(e.getID()))
    for edge in edges:
        if _is_internal_edge(edge):
            continue

        raw_shape = edge.getShape(includeJunctions=include_junctions)
        if not raw_shape or len(raw_shape) < 2:
            raw_shape = edge.getShape()

        wgs84_coords: list[list[float]] = []
        for x, y in raw_shape:
            lon, lat = net.convertXY2LonLat(x, y)
            wgs84_coords.append([round(float(lon), precision), round(float(lat), precision)])

        wgs84_coords = _deduplicate_coords(wgs84_coords)
        if len(wgs84_coords) < 2:
            # Extremely short edges (<0.2 m) can collapse after rounding; fall back to unrounded endpoints
            lon0, lat0 = net.convertXY2LonLat(*raw_shape[0])
            lon1, lat1 = net.convertXY2LonLat(*raw_shape[-1])
            wgs84_coords = [[float(lon0), float(lat0)], [float(lon1), float(lat1)]]

        edge_id = str(edge.getID())
        speed_ms = round(float(edge.getSpeed()), 2)

        features.append(
            {
                "type": "Feature",
                "id": edge_id,
                "geometry": {
                    "type": "LineString",
                    "coordinates": wgs84_coords,
                },
                "properties": {
                    "edgeId": edge_id,
                    "lanes": int(edge.getLaneNumber()),
                    "speed": speed_ms,
                    "speedKmh": round(speed_ms * 3.6, 1),
                    "name": str(edge.getName() or ""),
                    "highway": str(edge.getType() or ""),
                    "length": round(float(edge.getLength()), 2),
                    "fromNode": str(edge.getFromNode().getID()),
                    "toNode": str(edge.getToNode().getID()),
                },
            }
        )

    return {
        "type": "FeatureCollection",
        "features": features,
    }


def export_network_geojson(
    net_path: Path | str,
    output_path: Path | str,
    *,
    include_junctions: bool = True,
    precision: int = 6,
) -> dict[str, Any]:
    """Convert `net_path` to GeoJSON and write atomically to `output_path`."""
    geojson = net_to_geojson(
        net_path,
        include_junctions=include_junctions,
        precision=precision,
    )

    text = json.dumps(geojson, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    atomic_write_text(output_path, text)
    return geojson
