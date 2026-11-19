"""Path layout of the file-based data store (HLD MK5, §3.4.4).

All persistent data lives under one data root. This module only builds
and checks paths. It does not create folders or files.

Layout:
    <root>/base_network/
    <root>/demand/
    <root>/scenarios/<scenario_id>/
    <root>/jobs/<job_id>/
    <root>/results/<job_id>/
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

# backend/auris/storage/layout.py -> parents[3] is the repo root
_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_ROOT = _REPO_ROOT / "auris-data"


class InvalidIdError(ValueError):
    """Raised when an id is not a valid UUID in standard form."""


class DataLayout:
    """Builds the paths of the data store under one root folder."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).resolve()

    @classmethod
    def from_env(cls) -> DataLayout:
        """Use AURIS_DATA_DIR if set, otherwise <repo>/auris-data.

        A relative AURIS_DATA_DIR is resolved against the repo root.
        """
        value = os.environ.get("AURIS_DATA_DIR")
        if not value:
            return cls(_DEFAULT_ROOT)
        path = Path(value)
        return cls(path if path.is_absolute() else _REPO_ROOT / path)

    def base_network_dir(self) -> Path:
        return self.root / "base_network"

    def demand_dir(self) -> Path:
        return self.root / "demand"

    def scenario_dir(self, scenario_id: str) -> Path:
        return self._child("scenarios", scenario_id)

    def job_dir(self, job_id: str) -> Path:
        return self._child("jobs", job_id)

    def result_dir(self, job_id: str) -> Path:
        return self._child("results", job_id)

    def _child(self, area: str, item_id: str) -> Path:
        """Return <root>/<area>/<item_id> after checking that the id is safe."""
        _check_id(item_id)
        area_dir = (self.root / area).resolve()
        path = (area_dir / item_id).resolve()
        # Second line of defence: the final path must sit directly in the area folder.
        if path.parent != area_dir:
            raise InvalidIdError(f"{area} id leaves its folder: {item_id!r}")
        return path


def _check_id(item_id: object) -> None:
    """Accept only a UUID in standard form, for example 3f2a9c1e-7b4d-4e2a-9f1c-0d8e6a5b4c3d."""
    if not isinstance(item_id, str):
        raise InvalidIdError(f"id must be a string, got {type(item_id).__name__}")
    try:
        parsed = uuid.UUID(item_id)
    except ValueError:
        raise InvalidIdError(f"id is not a UUID: {item_id!r}") from None
    # uuid.UUID() also accepts upper case, braces, "urn:uuid:" and no dashes.
    # Only one spelling is allowed, so one id always maps to one folder.
    if str(parsed) != item_id:
        raise InvalidIdError(f"id is not in standard UUID form: {item_id!r}")
