"""Unit tests for auris.storage.atomic (SCRUM-11)."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from auris.storage import atomic
from auris.storage.atomic import atomic_write_bytes, atomic_write_json, atomic_write_text

OLD_CONTENT = b'{"status": "queued"}\n'


# Names of all files in a folder. Used to check that no temp file is left behind.
def _files(folder: Path) -> list[str]:
    return sorted(p.name for p in folder.iterdir())


# A target file that already has content, to check that a failed write does not change it.
@pytest.fixture
def existing_file(tmp_path: Path) -> Path:
    path = tmp_path / "status.json"
    path.write_bytes(OLD_CONTENT)
    return path


# --------------------------------------------------------------------------- normal writes


# Bytes are written exactly as given.
def test_write_bytes(tmp_path: Path) -> None:
    path = tmp_path / "data.bin"
    atomic_write_bytes(path, b"\x00\x01abc")
    assert path.read_bytes() == b"\x00\x01abc"


# Text is stored as UTF-8 and "\n" is not turned into "\r\n" on Windows.
def test_write_text_keeps_utf8_and_newlines(tmp_path: Path) -> None:
    path = tmp_path / "note.txt"
    atomic_write_text(path, "Kadıköy\nşehir\n")
    assert path.read_bytes() == "Kadıköy\nşehir\n".encode()


# JSON is indented, keeps non-ASCII letters and ends with a newline.
def test_write_json_format(tmp_path: Path) -> None:
    path = tmp_path / "job.json"
    atomic_write_json(path, {"name": "Kadıköy", "count": 2})
    assert path.read_text(encoding="utf-8") == '{\n  "name": "Kadıköy",\n  "count": 2\n}\n'


# A second write replaces the old content completely.
def test_overwrites_existing_file(existing_file: Path) -> None:
    atomic_write_json(existing_file, {"status": "done"})
    assert existing_file.read_text(encoding="utf-8") == '{\n  "status": "done"\n}\n'


# Missing parent folders, such as a new jobs/<id>/ folder, are created.
def test_creates_missing_parent_folders(tmp_path: Path) -> None:
    path = tmp_path / "jobs" / "some-id" / "job.json"
    atomic_write_json(path, {})
    assert path.is_file()


# The path may also be given as a plain string.
def test_accepts_str_path(tmp_path: Path) -> None:
    path = tmp_path / "data.bin"
    atomic_write_bytes(str(path), b"abc")
    assert path.read_bytes() == b"abc"


# After a successful write only the target file is in the folder.
def test_no_temp_file_left_after_success(tmp_path: Path) -> None:
    atomic_write_json(tmp_path / "job.json", {"a": 1})
    assert _files(tmp_path) == ["job.json"]


# The final file has normal rights (0o644), not the owner-only rights of a temp file.
@pytest.mark.skipif(os.name == "nt", reason="POSIX file modes do not apply on Windows")
def test_file_mode_is_644(tmp_path: Path) -> None:
    path = tmp_path / "job.json"
    atomic_write_json(path, {})
    assert stat.S_IMODE(path.stat().st_mode) == 0o644


# --------------------------------------------------------------------------- failed writes


# The rename step fails: the old file must stay unchanged and the temp file must be removed.
def test_failed_replace_keeps_old_file(existing_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def broken_replace(src, dst):
        raise OSError("simulated rename failure")

    monkeypatch.setattr(atomic.os, "replace", broken_replace)
    with pytest.raises(OSError, match="simulated"):
        atomic_write_json(existing_file, {"status": "done"})
    assert existing_file.read_bytes() == OLD_CONTENT
    assert _files(existing_file.parent) == ["status.json"]


# Writing to disk fails half way (fsync): same result, the old file is safe.
def test_failed_fsync_keeps_old_file(existing_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def broken_fsync(fd):
        raise OSError("simulated disk failure")

    monkeypatch.setattr(atomic.os, "fsync", broken_fsync)
    with pytest.raises(OSError, match="simulated"):
        atomic_write_json(existing_file, {"status": "done"})
    assert existing_file.read_bytes() == OLD_CONTENT
    assert _files(existing_file.parent) == ["status.json"]


# Ctrl+C during the write: the temp file is still removed and the interrupt is passed on.
def test_interrupt_cleans_up(existing_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def interrupted_fsync(fd):
        raise KeyboardInterrupt

    monkeypatch.setattr(atomic.os, "fsync", interrupted_fsync)
    with pytest.raises(KeyboardInterrupt):
        atomic_write_bytes(existing_file, b"new")
    assert existing_file.read_bytes() == OLD_CONTENT
    assert _files(existing_file.parent) == ["status.json"]


# A failed write to a new path leaves nothing behind: no target and no temp file.
def test_failed_write_to_new_file_leaves_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def broken_replace(src, dst):
        raise OSError("simulated rename failure")

    monkeypatch.setattr(atomic.os, "replace", broken_replace)
    with pytest.raises(OSError):
        atomic_write_bytes(tmp_path / "new.bin", b"abc")
    assert _files(tmp_path) == []


# Values that are not valid JSON fail before any file is touched.
@pytest.mark.parametrize(
    ("bad_obj", "error"),
    [
        ({"speed": float("nan")}, ValueError),  # JS JSON.parse cannot read NaN
        ({"speed": float("inf")}, ValueError),
        ({"ids": {1, 2}}, TypeError),  # a set has no JSON form
        ({"when": object()}, TypeError),
    ],
)
def test_bad_json_keeps_old_file(existing_file: Path, bad_obj: object, error: type[Exception]) -> None:
    with pytest.raises(error):
        atomic_write_json(existing_file, bad_obj)
    assert existing_file.read_bytes() == OLD_CONTENT
    assert _files(existing_file.parent) == ["status.json"]
