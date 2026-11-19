"""Atomic file writes for the file-based data store (HLD MK5, §3.4.4).

Data is first written to a temporary file in the same folder. When it is
complete and on disk, os.replace() puts it over the target in one step.
Readers see either the old file or the new file, never a half-written one.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def atomic_write_bytes(path: Path | str, data: bytes) -> None:
    """Write bytes to path atomically. Creates missing parent folders."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # The temp file must be in the same folder: os.replace is only atomic on one file system.
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())  # make sure the data is on disk before the rename
        # mkstemp creates the file as owner-only (0o600); use normal file rights instead.
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def atomic_write_text(path: Path | str, text: str) -> None:
    """Write text as UTF-8. Line endings are kept as given, also on Windows."""
    atomic_write_bytes(path, text.encode("utf-8"))


def atomic_write_json(path: Path | str, obj: Any) -> None:
    """Write obj as pretty JSON with a final newline.

    The object is converted before any file is touched, so a value that
    cannot be converted leaves the disk unchanged.
    """
    text = json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    atomic_write_text(path, text)
