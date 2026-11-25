"""Unit tests for SUMO `.net.xml` -> WGS84 GeoJSON export (SCRUM-19)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from auris.network.geojson_exporter import export_network_geojson, net_to_geojson

REPO_ROOT = Path(__file__).resolve().parents[3]
BASE_NET_XML = REPO_ROOT / "auris-data" / "base_network" / "base.net.xml"

# Midtown East pilot region bounding box (with small margin for UTM/edge extensions)
MIN_LON, MAX_LON = -73.98, -73.96
MIN_LAT, MAX_LAT = 40.75, 40.77


@pytest.fixture(scope="module")
def pilot_geojson() -> dict:
    assert BASE_NET_XML.is_file(), f"Missing base network fixture: {BASE_NET_XML}"
    return net_to_geojson(BASE_NET_XML)


def test_feature_collection_structure(pilot_geojson: dict) -> None:
    assert pilot_geojson["type"] == "FeatureCollection"
    features = pilot_geojson["features"]
    assert isinstance(features, list)
    assert len(features) == 101  # All non-internal edges of base.net.xml


def test_required_properties_and_types(pilot_geojson: dict) -> None:
    for feat in pilot_geojson["features"]:
        assert feat["type"] == "Feature"
        props = feat["properties"]

        assert isinstance(props["edgeId"], str) and props["edgeId"]
        assert isinstance(props["lanes"], int) and props["lanes"] >= 1
        assert isinstance(props["speed"], float) and 0 < props["speed"] < 20.0


def test_internal_edges_are_excluded(pilot_geojson: dict) -> None:
    for feat in pilot_geojson["features"]:
        edge_id = feat["properties"]["edgeId"]
        assert not edge_id.startswith(":"), f"Internal edge leaked into GeoJSON: {edge_id}"


def test_linestring_wgs84_coordinates_in_pilot_region(pilot_geojson: dict) -> None:
    for feat in pilot_geojson["features"]:
        geom = feat["geometry"]
        assert geom["type"] == "LineString"
        coords = geom["coordinates"]
        assert len(coords) >= 2
        for lon, lat in coords:
            assert MIN_LON <= lon <= MAX_LON, f"Longitude out of Midtown East bounds: {lon}"
            assert MIN_LAT <= lat <= MAX_LAT, f"Latitude out of Midtown East bounds: {lat}"


def test_export_writes_deterministic_json(tmp_path: Path) -> None:
    out1 = tmp_path / "net1.geojson"
    out2 = tmp_path / "net2.geojson"

    export_network_geojson(BASE_NET_XML, out1)
    export_network_geojson(BASE_NET_XML, out2)

    raw1 = out1.read_text(encoding="utf-8")
    raw2 = out2.read_text(encoding="utf-8")
    assert raw1 == raw2

    parsed = json.loads(raw1)
    assert parsed["type"] == "FeatureCollection"
    assert len(parsed["features"]) == 101


def test_missing_input_raises_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        net_to_geojson(tmp_path / "does_not_exist.net.xml")
