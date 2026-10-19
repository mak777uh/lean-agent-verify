"""Compile a composed proof file and read the two facts a checker cares about.

1. does it elaborate at all (inside the wall-clock budget), and
2. which axioms does the entry theorem actually depend on.

Lean reports (2) itself: ``#print axioms proof`` prints
``'proof' depends on axioms: [propext, Classical.choice, Quot.sound]``.
``#check proof`` gives the direction (``proof : statementProp`` vs
``proof : ¬statementProp``), which the checker uses to decide "proved" vs
"disproved".
"""
from __future__ import annotations

import re
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from .toolchain import Toolchain

AXIOM_LINE = re.compile(r"depends on axioms:\s*\[(.*?)\]", re.S)
TYPE_LINE = re.compile(r"^(proof|disproof)\s*:\s*(.+)$", re.M)
ERROR_LINE = re.compile(r"^(.*?):(\d+):(\d+):\s*(error.*)$", re.M)


@dataclass
class CompileResult:
    exit_code: int
    timed_out: bool
    seconds: float
    axioms: list[str] = field(default_factory=list)
    entry_type: str = ""
    errors: list[str] = field(default_factory=list)
    raw: str = ""

    @property
    def ok(self) -> bool:
        return not self.timed_out and self.exit_code == 0 and not self.errors

    def summary(self) -> str:
        state = "OK" if self.ok else ("TIMEOUT" if self.timed_out else "FAIL")
        return (f"{state} exit={self.exit_code} {self.seconds:.1f}s "
                f"axioms={self.axioms or '[]'} entry={self.entry_type or '?'}")


def parse(output: str) -> tuple[list[str], str, list[str]]:
    """Extract (axioms, entry-theorem type, errors) from Lean's stdout+stderr."""
    axioms: list[str] = []
    m = AXIOM_LINE.search(output)
    if m:
        axioms = sorted({tok.strip() for tok in m.group(1).split(",") if tok.strip()})
    entry = ""
    t = TYPE_LINE.search(output)
    if t:
        entry = f"{t.group(1)} : {t.group(2).strip()}"
    errors = [f"{e.group(1)}:{e.group(2)}:{e.group(3)}: {e.group(4)}"
              for e in ERROR_LINE.finditer(output)]
    return axioms, entry, errors


def run(tc: Toolchain, source: str, *, timeout: int = 600,
        workdir: str | Path | None = None, filename: str = "Composed.lean") -> CompileResult:
    """Write `source` to a scratch file and elaborate it with the given toolchain."""
    tmpdir = Path(tempfile.mkdtemp(prefix="preflight-")) if workdir is None else Path(workdir)
    tmpdir.mkdir(parents=True, exist_ok=True)
    path = tmpdir / filename
    path.write_text(source, encoding="utf-8")

    started = time.time()
    timed_out = False
    try:
        proc = subprocess.run([tc.lean, filename], cwd=str(tmpdir), env=tc.env,
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout)
        out = (proc.stdout or "") + (proc.stderr or "")
        code = proc.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        out = ((exc.stdout or "") if isinstance(exc.stdout, str) else "") + "\n"
        code = -1
    seconds = time.time() - started

    axioms, entry, errors = parse(out)
    return CompileResult(code, timed_out, seconds, axioms, entry, errors, out)
