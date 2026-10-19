"""Locate a Lean binary and the environment that resolves a pinned Mathlib.

A checker runs the proof inside a prebuilt environment: a specific toolchain plus
a pinned Mathlib whose oleans are already on disk. `lake env` produces exactly
such an environment (``LEAN_PATH`` / ``LEAN_SRC_PATH``), so the supported input
here is a captured ``KEY=VALUE`` environment file - no paths baked into the code.

Three ways to point at a toolchain, in priority order:

1. ``--lean /path/to/lean``
2. ``LEAN_BIN`` environment variable
3. ``lean`` on ``PATH``
"""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

# Variables a lake-produced environment needs; everything else is inherited.
PASSTHROUGH_KEYS = ("LEAN_PATH", "LEAN_SRC_PATH", "LEAN_SYSROOT", "LAKE_HOME", "PATH")


@dataclass
class Toolchain:
    lean: str
    env: dict[str, str]

    def describe(self) -> str:
        leanpath = self.env.get("LEAN_PATH", "")
        roots = [p for p in leanpath.split(os.pathsep) if p]
        return (f"lean={self.lean}  LEAN_PATH entries={len(roots)}"
                + (f"  first={roots[0]}" if roots else "  (LEAN_PATH unset)"))


def load_env_file(path: str | Path) -> dict[str, str]:
    """Read ``KEY=VALUE`` lines (as printed by ``lake env <cmd>``)."""
    env: dict[str, str] = {}
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        name, _, value = line.partition("=")
        if name in PASSTHROUGH_KEYS:
            env[name] = value
    return env


def resolve(lean: str | None = None, env_file: str | Path | None = None) -> Toolchain:
    binary = lean or os.environ.get("LEAN_BIN") or shutil.which("lean")
    if not binary:
        raise FileNotFoundError(
            "no Lean binary: pass --lean, set LEAN_BIN, or put `lean` on PATH")
    env = dict(os.environ)
    if env_file:
        env.update(load_env_file(env_file))
    return Toolchain(binary, env)


def version(tc: Toolchain) -> str:
    import subprocess
    try:
        proc = subprocess.run([tc.lean, "--version"], capture_output=True, text=True,
                              env=tc.env, timeout=120)
        return (proc.stdout or proc.stderr).strip()
    except Exception as exc:  # noqa: BLE001 - diagnostics only
        return f"<unavailable: {exc}>"
