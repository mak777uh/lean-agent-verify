"""Policy model for Lean proof-bounty checkers.

The values here mirror a published attester policy document (see
``docs/reproducing.md``); nothing is hard-coded to any private deployment.
A deployment is described by passing ``--policy policy.json``.

Recognised keys (all optional, defaults below):

    toolchain        Lean toolchain id, e.g. "leanprover/lean4:v4.30.0"
    mathlib_rev      Mathlib commit the checker pins
    statement_def    name of the statement definition, default "statementProp"
    entry_theorem    name of the theorem the checker looks for, default "proof"
    axiom_allowlist  axioms a proof may depend on
    import_allowlist module-name prefixes a proof may import
    reject_sorry     reject `sorry`/`sorryAx`
    max_build_secs   wall-clock budget for one check
    max_artifact_bytes
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_AXIOMS = ["propext", "Classical.choice", "Quot.sound"]


@dataclass
class Policy:
    toolchain: str = "leanprover/lean4:v4.30.0"
    mathlib_rev: str | None = None
    statement_def: str = "statementProp"
    entry_theorem: str = "proof"
    axiom_allowlist: list[str] = field(default_factory=lambda: list(DEFAULT_AXIOMS))
    import_allowlist: list[str] = field(default_factory=lambda: ["Mathlib"])
    reject_sorry: bool = True
    max_build_secs: int = 600
    max_artifact_bytes: int = 5 * 1024 * 1024

    @classmethod
    def from_json(cls, path: str | Path) -> "Policy":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})

    def allows_import(self, module: str) -> bool:
        """A module is allowed when it equals an allowlist prefix or starts with it + '.'"""
        for prefix in self.import_allowlist:
            if module == prefix or module.startswith(prefix + "."):
                return True
        return False
