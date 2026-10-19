"""Static scan for tokens that bounty checkers reject *before* they compile.

Why this module exists
----------------------
A proof was submitted, confirmed on Solana, and reached `verified` - with score
0 and no payment. The checker's `check_detail` read:

    proof contains forbidden token `scoped` (policy rejects meta commands)

The Lean file was correct (it compiles, axiom set = the allowlist), but it began
with `open scoped BigOperators`. The checker scans the *artifact source* for
meta-commands and rejects it before Lean ever runs. Cost of that lesson:
0.00111744 SOL and one bounty. See ``incidents/``.

Every entry below carries the reason it is here, so the list stays honest:
tokens marked ``observed`` were seen rejected in the wild, ``inferred`` ones are
Lean meta-commands that a "no meta commands" policy almost certainly covers.
Run ``python -m preflight tokens`` to print the table.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ForbiddenToken:
    token: str
    rationale: str
    evidence: str  # "observed" | "inferred"


TOKENS: tuple[ForbiddenToken, ...] = (
    ForbiddenToken("scoped", "scoped notation/attribute scope command",
                   "observed: checker reply 2026-10-19T17:52:12Z, "
                   "'proof contains forbidden token `scoped` (policy rejects meta commands)'"),
    ForbiddenToken("namespace", "opens a declaration namespace",
                   "inferred: artifact must not wrap declarations; checkers require a "
                   "flat file so the entry theorem stays a root declaration"),
    ForbiddenToken("unsafe", "escapes the kernel",
                   "inferred: a proof depending on unsafe code is not machine-checked"),
    ForbiddenToken("axiom", "declares an unproved assumption",
                   "inferred: equivalent to assuming the goal; rejected on principle"),
    ForbiddenToken("macro", "defines a tactic/syntax macro",
                   "inferred: lets a proof smuggle in arbitrary syntax"),
    ForbiddenToken("elab", "elaborator extension",
                   "inferred: meta-programming surface"),
    ForbiddenToken("syntax", "adds surface syntax",
                   "inferred: meta-programming surface"),
    ForbiddenToken("run_tac", "runs arbitrary tactic code at elaboration time",
                   "inferred: arbitrary code execution inside the checker"),
    ForbiddenToken("#eval", "compiles/executes a term at elaboration time",
                   "inferred: arbitrary code execution inside the checker"),
    ForbiddenToken("set_option", "changes elaborator options",
                   "inferred: can weaken checks (e.g. autoImplicit, maxHeartbeats)"),
    ForbiddenToken("sorry", "admits the goal",
                   "observed in spirit: reject_sorry policies name sorryAx explicitly"),
    ForbiddenToken("attribute", "registers attributes/instances globally",
                   "inferred: global side effects on the checker environment"),
)


@dataclass
class Finding:
    token: str
    line: int
    text: str
    rationale: str
    evidence: str

    def __str__(self) -> str:
        return f"line {self.line}: forbidden token {self.token!r} ({self.evidence}) - {self.rationale}"


def strip_comments(source: str) -> str:
    """Remove comments so a token mentioned in prose is not a false positive.

    Lean block comments nest, so a depth counter is used rather than a regex.
    """
    out: list[str] = []
    depth = 0
    i = 0
    n = len(source)
    while i < n:
        two = source[i:i + 2]
        if depth == 0 and two == "--":
            j = source.find("\n", i)
            i = n if j == -1 else j
            continue
        if two == "/-":
            depth += 1
            i += 2
            continue
        if two == "-/" and depth:
            depth -= 1
            i += 2
            continue
        if depth == 0:
            out.append(source[i])
        i += 1
    return "".join(out)


def scan(source: str) -> list[Finding]:
    """Return every forbidden token occurrence in code (comments ignored)."""
    code = strip_comments(source)
    findings: list[Finding] = []
    for lineno, text in enumerate(code.splitlines(), 1):
        for token in TOKENS:
            if token.token in text:
                findings.append(Finding(token.token, lineno, text.strip(),
                                        token.rationale, token.evidence))
    return findings


def table() -> str:
    width = max(len(t.token) for t in TOKENS)
    rows = [f"{'token'.ljust(width)}  evidence   reason"]
    for t in TOKENS:
        rows.append(f"{t.token.ljust(width)}  {t.evidence:<9}  {t.rationale}")
    return "\n".join(rows)


_INLINE_BLOCK = re.compile(r"/-[\s\S]*?-/")
