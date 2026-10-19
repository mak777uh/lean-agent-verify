"""Result models and rendering for a preflight run."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


OK, FAIL, SKIP = "ok", "fail", "skipped"


@dataclass
class Check:
    name: str
    status: str
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"check": self.name, "status": self.status, "detail": self.detail}

    def line(self) -> str:
        mark = {OK: "PASS", FAIL: "FAIL", SKIP: "SKIP"}[self.status]
        return f"  [{mark}] {self.name}" + (f" - {self.detail}" if self.detail else "")


@dataclass
class Report:
    artifact: str
    statement: str
    checks: list[Check] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return all(c.status != FAIL for c in self.checks)

    def add(self, name: str, status: str, detail: str = "") -> None:
        self.checks.append(Check(name, status, detail))

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact": self.artifact,
            "statement": self.statement,
            "passed": self.passed,
            "checks": [c.to_dict() for c in self.checks],
            "meta": self.meta,
        }

    def render(self) -> str:
        head = "PASS - safe to claim/submit" if self.passed else "FAIL - do not submit"
        lines = [f"artifact : {self.artifact}", f"statement: {self.statement}", ""]
        lines += [c.line() for c in self.checks]
        lines += ["", f"==== {head} ===="]
        return "\n".join(lines)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
