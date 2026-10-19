"""Compose a checker's compilation unit from a campaign statement + an artifact.

Observed checker behaviour (documented in the public bounty repository's own
notes and reproduced by experiment): the checker **prepends the campaign
statement** to the submitted artifact and compiles the result. Consequences a
submitter must respect:

* the artifact must NOT redeclare the statement (``... has already been declared``
  -> score 0, escrow refunded, indistinguishable from a wrong proof);
* the artifact must carry the ``import`` lines its proof needs, because the
  statement's own imports are usually a narrow subset - and the checker
  validates those imports against its allowlist;
* therefore imports from both sides have to end up at the top of one file.

This module performs that composition, which is also the only honest way to
test an artifact locally.
"""
from __future__ import annotations

from dataclasses import dataclass


IMPORT = "import "


def _split_imports(source: str) -> tuple[list[str], str]:
    imports = [ln.strip() for ln in source.splitlines() if ln.startswith(IMPORT)]
    body = "\n".join(ln for ln in source.splitlines() if not ln.startswith(IMPORT))
    return imports, body


@dataclass
class Composed:
    source: str
    imports: list[str]

    def summary(self) -> str:
        return f"{len(self.imports)} import(s): " + ", ".join(i[len(IMPORT):] for i in self.imports)


def compose(statement: str, artifact: str, extra_probes: str = "") -> Composed:
    """Statement prepended, artifact's imports hoisted to the file header.

    ``extra_probes`` is appended verbatim (e.g. ``#print axioms proof``), which is
    how the checker reports what a proof actually rests on.
    """
    stmt_imports, stmt_body = _split_imports(statement.rstrip("\n"))
    art_imports, art_body = _split_imports(artifact.rstrip("\n"))

    imports: list[str] = []
    for line in stmt_imports + art_imports:
        if line not in imports:
            imports.append(line)

    parts = [
        "\n".join(imports),
        "",
        stmt_body.strip("\n"),
        "",
        art_body.strip("\n"),
    ]
    if extra_probes:
        parts += ["", extra_probes.strip("\n")]
    return Composed("\n".join(parts).rstrip("\n") + "\n", imports)


def check_import_allowlist(imports: list[str], allows) -> list[str]:
    """Return the import lines whose module is outside the policy allowlist."""
    bad = []
    for line in imports:
        module = line[len(IMPORT):].strip()
        if not allows(module):
            bad.append(line)
    return bad


def find_redeclarations(artifact: str, names: list[str]) -> list[str]:
    """Names the artifact declares that the campaign already provides."""
    found = []
    for line in artifact.splitlines():
        stripped = line.lstrip()
        if not stripped or stripped.startswith("--"):
            continue
        head = stripped.split()
        if len(head) >= 2 and head[0] in {"def", "theorem", "lemma", "abbrev", "noncomputable"}:
            target = head[1] if head[0] != "noncomputable" else (head[2] if len(head) > 2 else "")
            if target in names:
                found.append(target)
    return found
