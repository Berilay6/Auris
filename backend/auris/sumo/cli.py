"""Thin subprocess wrappers for Eclipse SUMO CLI binaries (netconvert, sumo, duarouter, sumo-gui).

Follows HLD MK1 (SUMO as a black-box CLI tool). Binary and SUMO_HOME discovery works across:
  1. `$SUMO_HOME` environment variable (e.g. Docker container)
  2. Native installation bundled inside pip-installed `eclipse-sumo` (`sumo.SUMO_HOME`)
  3. Active Python environment's Scripts/bin folder
  4. System `PATH`
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


class SumoNotFoundError(FileNotFoundError):
    """Raised when a required SUMO executable or SUMO_HOME cannot be located."""


class SumoCommandError(RuntimeError):
    """Raised when a SUMO CLI command exits with a non-zero status."""

    def __init__(self, cmd: list[str], returncode: int, stderr: str) -> None:
        self.cmd = cmd
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(
            f"SUMO command failed (exit={returncode}): {' '.join(cmd)}\n{stderr.strip()}"
        )


def find_sumo_home() -> Path:
    """Resolve SUMO_HOME: environment variable if set, otherwise `import sumo; sumo.SUMO_HOME`."""
    env_home = os.environ.get("SUMO_HOME")
    if env_home:
        path = Path(env_home).resolve()
        if path.is_dir():
            return path
        raise SumoNotFoundError(f"SUMO_HOME points to a missing directory: {path}")

    try:
        import sumo  # type: ignore[import-not-found]

        pkg_home = getattr(sumo, "SUMO_HOME", None)
        if pkg_home:
            path = Path(pkg_home).resolve()
            if path.is_dir():
                return path
    except ImportError:
        pass

    raise SumoNotFoundError(
        "SUMO_HOME is not set and `eclipse-sumo` package is not installed. "
        "Install `eclipse-sumo==1.28.0` or set SUMO_HOME."
    )


def find_sumo_binary(name: str) -> Path:
    """Locate a SUMO binary (e.g. 'netconvert', 'sumo', 'sumo-gui', 'duarouter')."""
    suffixes = (".exe", "") if os.name == "nt" else ("",)
    candidates: list[Path] = []

    # 1. Native binary bundled inside pip-installed `eclipse-sumo` (avoids pythonw.exe wrapper issues on Windows)
    try:
        import sumo  # type: ignore[import-not-found]

        pkg_home = getattr(sumo, "SUMO_HOME", None)
        if pkg_home:
            for sfx in suffixes:
                candidates.append(Path(pkg_home) / "bin" / f"{name}{sfx}")
    except ImportError:
        pass

    # 2. $SUMO_HOME/bin
    sumo_home = os.environ.get("SUMO_HOME")
    if sumo_home:
        for sfx in suffixes:
            candidates.append(Path(sumo_home) / "bin" / f"{name}{sfx}")

    # 3. Active Python venv/bin directory
    py_bin = Path(sys.executable).resolve().parent
    for sfx in suffixes:
        candidates.append(py_bin / f"{name}{sfx}")

    for cand in candidates:
        if cand.is_file():
            return cand

    # 4. System PATH
    found = shutil.which(name)
    if found:
        return Path(found).resolve()

    raise SumoNotFoundError(
        f"SUMO binary '{name}' not found. Install Eclipse SUMO (or `pip install eclipse-sumo`) "
        f"or set SUMO_HOME."
    )


def get_binary_version(binary: Path) -> str:
    """Return the first version line reported by `<binary> --version`."""
    res = subprocess.run(
        [str(binary), "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    first_line = (res.stdout or res.stderr).strip().splitlines()
    return first_line[0].strip() if first_line else "unknown"


def run_netconvert(
    netccfg: Path,
    *,
    osm_file: Path | None = None,
    output_file: Path | None = None,
    extra_args: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run `netconvert` using a `.netccfg` file and optional path overrides."""
    netconvert = find_sumo_binary("netconvert")
    cmd = [str(netconvert), "-c", str(netccfg)]
    if osm_file is not None:
        cmd += ["--osm-files", str(osm_file)]
    if output_file is not None:
        cmd += ["--output-file", str(output_file)]
    if extra_args:
        cmd += list(extra_args)

    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if res.returncode != 0:
        raise SumoCommandError(cmd, res.returncode, res.stderr)
    return res
