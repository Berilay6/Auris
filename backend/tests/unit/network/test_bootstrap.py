"""Unit tests for immutable base network generation and checksum helpers (SCRUM-6)."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from auris.network.bootstrap import (
    load_netconvert_boundary,
    normalize_net_xml_header,
    sha256_of,
    sha256_of_text,
)
from auris.storage.layout import DataLayout

REPO_ROOT = Path(__file__).resolve().parents[4]
PILOT_CONFIG = REPO_ROOT / "config" / "pilot_region.yaml"
BASE_NET_DIR = DataLayout(REPO_ROOT / "auris-data").base_network_dir()
BASE_NET_XML = BASE_NET_DIR / "base.net.xml"
BASE_NET_META = BASE_NET_DIR / "base.net.xml.meta.json"


def test_sha256_of_text_is_identical_for_crlf_and_lf(tmp_path: Path) -> None:
    lf_file = tmp_path / "sample_lf.xml"
    crlf_file = tmp_path / "sample_crlf.xml"

    lf_bytes = b"<net>\n  <edge id='e1'/>\n</net>\n"
    crlf_bytes = b"<net>\r\n  <edge id='e1'/>\r\n</net>\r\n"

    lf_file.write_bytes(lf_bytes)
    crlf_file.write_bytes(crlf_bytes)

    assert sha256_of(lf_file) != sha256_of(crlf_file)
    assert sha256_of_text(lf_file) == sha256_of_text(crlf_file)


def test_normalize_net_xml_header_strips_carriage_returns_and_paths() -> None:
    raw = (
        '<?xml version="1.0" encoding="UTF-8"?>\r\n'
        "<!-- generated on 2026-11-25 10:00:00 by Eclipse SUMO netconvert 1.28.0\r\n"
        '    <osm-files value="C:\\abs\\midtown_east.osm"/>\r\n'
        '    <output-file value="/tmp/xyz/base.net.xml"/>\r\n'
        '    <type-files value="C:\\sumo\\osmNetconvert.typ.xml,C:\\cfg\\osm-speeds.typ.xml"/>\r\n'
        "-->\r\n"
        "<net/>\r\n"
    )
    out = normalize_net_xml_header(
        raw,
        snapshot_date="2026-10-01T00:00:00Z",
        osm_name="midtown_east.osm",
        out_name="base.net.xml",
        type_names="osmNetconvert.typ.xml,osm-speeds.typ.xml",
    )
    assert "\r" not in out
    assert "2026-10-01T00:00:00Z" in out
    assert 'value="midtown_east.osm"' in out
    assert 'value="base.net.xml"' in out
    assert 'value="osmNetconvert.typ.xml,osm-speeds.typ.xml"' in out


def test_load_netconvert_boundary_reads_unbuffered_polygon() -> None:
    boundary = load_netconvert_boundary(PILOT_CONFIG)
    coords = [float(v) for v in boundary.split(",")]
    # 5 [lon, lat] pairs (closed 4-corner ring) = 10 floats
    assert len(coords) == 10
    assert (coords[0], coords[1]) == (coords[-2], coords[-1])


def test_missing_pilot_config_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_netconvert_boundary(tmp_path / "missing.yaml")


def test_generated_base_network_uses_lf_and_matches_meta() -> None:
    assert BASE_NET_XML.is_file(), f"Missing {BASE_NET_XML}"
    assert BASE_NET_META.is_file(), f"Missing {BASE_NET_META}"

    raw_bytes = BASE_NET_XML.read_bytes()
    assert b"\r" not in raw_bytes, "base.net.xml must use LF line endings only"

    meta_bytes = BASE_NET_META.read_bytes()
    assert b"\r" not in meta_bytes, "base.net.xml.meta.json must use LF line endings only"

    meta = json.loads(meta_bytes.decode("utf-8"))
    assert sha256_of(BASE_NET_XML) == meta["sha256"]
    assert meta["typemap_file"] == "osm-speeds.typ.xml"
    assert meta["typemap_sha256"]


def test_base_network_speeds_and_primary_link_restored() -> None:
    text = BASE_NET_XML.read_text(encoding="utf-8")
    # A1: No lane or type should carry SUMO's 27.78 m/s (100 km/h) fallback speed
    assert 'speed="27.78"' not in text

    # A7: OSM way 993383311 (primary_link near 3rd Ave & E 58th St) must be present
    root = ET.fromstring(text)
    normal_edge_ids = [
        e.get("id", "") for e in root.findall("edge") if e.get("function") != "internal"
    ]
    assert any("993383311" in eid for eid in normal_edge_ids), (
        "Expected primary_link way 993383311 to be retained in base.net.xml"
    )
