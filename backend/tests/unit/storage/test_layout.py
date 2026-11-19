"""Unit tests for auris.storage.layout (SCRUM-11)."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

from auris.storage import layout as layout_module
from auris.storage.layout import DataLayout, InvalidIdError

VALID_ID = "3f2a9c1e-7b4d-4e2a-9f1c-0d8e6a5b4c3d"


# A DataLayout whose root is a fresh temporary folder, so tests never touch real data.
@pytest.fixture
def layout(tmp_path: Path) -> DataLayout:
    return DataLayout(tmp_path)


# --------------------------------------------------------------------------- path building


# base_network and demand have no id, so their paths are fixed under the root.
def test_fixed_dirs(layout: DataLayout, tmp_path: Path) -> None:
    root = tmp_path.resolve()
    assert layout.base_network_dir() == root / "base_network"
    assert layout.demand_dir() == root / "demand"


# Each id-based method builds <root>/<area>/<id>. Runs once per area.
@pytest.mark.parametrize(
    ("method", "area"),
    [("scenario_dir", "scenarios"), ("job_dir", "jobs"), ("result_dir", "results")],
)
def test_id_dirs(layout: DataLayout, tmp_path: Path, method: str, area: str) -> None:
    path = getattr(layout, method)(VALID_ID)
    assert path == tmp_path.resolve() / area / VALID_ID


# A freshly generated UUID, as the stores will create, is accepted.
def test_new_uuid4_is_accepted(layout: DataLayout) -> None:
    new_id = str(uuid.uuid4())
    assert layout.job_dir(new_id).name == new_id


# layout only computes paths. Calling it must leave the disk unchanged.
def test_does_not_create_folders(layout: DataLayout, tmp_path: Path) -> None:
    layout.base_network_dir()
    layout.job_dir(VALID_ID)
    assert list(tmp_path.iterdir()) == []


# --------------------------------------------------------------------------- id checks


# Path escapes (../), separators, absolute paths and other UUID spellings are rejected by all three id-based methods.
@pytest.mark.parametrize(
    "bad_id",
    [
        "",
        "..",
        "../x",
        "../../etc",
        "a/b",
        "a\\b",
        "/etc/passwd",
        "C:\\Windows",
        VALID_ID + "/..",
        "../" + VALID_ID,
        VALID_ID.upper(),  # same UUID, other spelling
        "{" + VALID_ID + "}",
        "urn:uuid:" + VALID_ID,
        VALID_ID.replace("-", ""),
        VALID_ID + "\n",  # hidden newline at the end
        " " + VALID_ID,  # hidden space at the start
    ],
)
def test_rejects_bad_ids(layout: DataLayout, bad_id: str) -> None:
    for method in (layout.scenario_dir, layout.job_dir, layout.result_dir):
        with pytest.raises(InvalidIdError):
            method(bad_id)


# Only str ids are accepted. A UUID object or bytes must be converted by the caller.
@pytest.mark.parametrize("bad_id", [None, 123, uuid.UUID(VALID_ID), b"abc"])
def test_rejects_non_string_ids(layout: DataLayout, bad_id: object) -> None:
    with pytest.raises(InvalidIdError):
        layout.job_dir(bad_id)  # type: ignore[arg-type]


# Callers such as the API can catch ValueError and return HTTP 400.
def test_invalid_id_error_is_value_error() -> None:
    assert issubclass(InvalidIdError, ValueError)


# Second line of defence: a valid id whose folder is a link to outside the root.
# Skipped on Windows when the user may not create symlinks.
def test_rejects_id_folder_that_links_outside(layout: DataLayout, tmp_path: Path) -> None:
    outside = tmp_path.parent / f"outside-{uuid.uuid4()}"
    outside.mkdir()
    (tmp_path / "jobs").mkdir()
    try:
        os.symlink(outside, tmp_path / "jobs" / VALID_ID, target_is_directory=True)
    except OSError:
        pytest.skip("creating symlinks is not allowed on this machine")
    with pytest.raises(InvalidIdError):
        layout.job_dir(VALID_ID)


# --------------------------------------------------------------------------- from_env


# An absolute AURIS_DATA_DIR (as in Docker: /data) is used as it is.
def test_from_env_absolute(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AURIS_DATA_DIR", str(tmp_path))
    assert DataLayout.from_env().root == tmp_path.resolve()


# A relative AURIS_DATA_DIR (as in .env: ./auris-data) starts at the repo root.
def test_from_env_relative_uses_repo_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AURIS_DATA_DIR", "./some-data")
    expected = (layout_module._REPO_ROOT / "some-data").resolve()
    assert DataLayout.from_env().root == expected


# Without AURIS_DATA_DIR the root is <repo>/auris-data.
def test_from_env_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AURIS_DATA_DIR", raising=False)
    expected = (layout_module._REPO_ROOT / "auris-data").resolve()
    assert DataLayout.from_env().root == expected
