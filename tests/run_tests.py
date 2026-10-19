#!/usr/bin/env python3
"""Test suite for preflight.

Fast: everything here runs in well under a second and needs no Lean toolchain,
because the checks that cost a bounty are precisely the cheap static ones.
Pass ``--with-lean PATH`` to additionally compile the reference statements.

    python tests/run_tests.py
    python tests/run_tests.py --with-lean ~/.elan/toolchains/<tc>/bin/lean

Exit code 0 when every expectation holds.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from preflight import Policy, compose, scan_tokens            # noqa: E402
from preflight.compile import parse                          # noqa: E402

ART = ROOT / "tests" / "artifacts"
REF = ROOT / "reference"

# (artifact, statement, expected passed?)
CASES = [
    ("ok_minimal.lean", "add-zero.lean", True),
    ("ok_comment_mentions_scoped.lean", "add-zero.lean", True),
    ("fail_scoped.lean", "add-zero.lean", False),
    ("fail_sorry.lean", "add-zero.lean", False),
    ("fail_axiom.lean", "add-zero.lean", False),
    ("fail_redeclares_statement.lean", "add-zero.lean", False),
    ("fail_no_entry_theorem.lean", "add-zero.lean", False),
]

failures: list[str] = []


def expect(cond: bool, label: str) -> None:
    print(("  ok   " if cond else "  FAIL ") + label)
    if not cond:
        failures.append(label)


def test_scanner() -> None:
    print("scanner")
    expect(scan_tokens("theorem proof : Q := by trivial") == [], "clean artifact has no findings")
    expect(len(scan_tokens("open scoped BigOperators")) == 1, "`scoped` is caught")
    expect(len(scan_tokens("theorem x : P := by sorry")) == 1, "`sorry` is caught")
    expect(len(scan_tokens("axiom cheat : P")) == 1, "`axiom` is caught")
    expect(len(scan_tokens("run_tac Lean.logInfo \"x\"")) == 1, "`run_tac` is caught")
    # comments are not commands
    expect(scan_tokens("/- sorry axiom scoped -/\ntheorem x : True := trivial") == [],
           "block comment does not trip the scanner")
    expect(scan_tokens("-- scoped axiom\ntheorem x : True := trivial") == [],
           "line comment does not trip the scanner")
    nested = "/- outer /- inner sorry -/ still comment -/\ntheorem x : True := trivial"
    expect(scan_tokens(nested) == [], "nested block comment does not trip the scanner")


def test_composition() -> None:
    print("composition")
    stmt = "import Mathlib.Data.Int.Basic\n\ndef statementProp : Prop := True\n"
    art = "import Mathlib.Tactic\ntheorem proof : statementProp := trivial\n"
    c = compose(stmt, art)
    imports = [l for l in c.source.splitlines() if l.startswith("import ")]
    first_decl = next(i for i, l in enumerate(c.source.splitlines())
                      if not l.startswith("import ") and l.strip())
    expect(len(imports) == 2, "both sides' imports are hoisted to the header")
    expect(all(i < first_decl for i, l in enumerate(c.source.splitlines())
               if l.startswith("import ")),
           "no import appears after a declaration")
    expect(c.source.index("def statementProp") < c.source.index("theorem proof"),
           "statement is prepended before the artifact")


def test_allowlist_and_axioms() -> None:
    print("policy")
    p = Policy()
    expect(p.allows_import("Mathlib.Tactic.Ring"), "Mathlib.Tactic.Ring allowed")
    expect(p.allows_import("Mathlib"), "bare Mathlib allowed")
    expect(not p.allows_import("Unregistered.Attacker"), "foreign module rejected")
    expect(not p.allows_import("MathlibExtra"), "prefix must stop at a module boundary")

    print("axiom parsing")
    good = "'proof' depends on axioms: [propext, Classical.choice, Quot.sound]"
    bad = "'proof' depends on axioms: [propext, Lean.ofReduceBool]"
    empty = "'proof' depends on axioms: []"
    expect(parse(good)[0] == ["Classical.choice", "Quot.sound", "propext"], "allowlisted set parsed")
    extra = [a for a in parse(bad)[0] if a not in Policy().axiom_allowlist]
    expect(extra == ["Lean.ofReduceBool"], "native_decide style axiom is flagged")
    expect(parse(empty)[0] == [], "empty axiom set parsed")


def test_cases() -> int:
    """Run the artifact matrix through the same code path the CLI uses."""
    print("artifact matrix")
    from preflight.cli import _static_checks  # noqa: PLC0415 - local by design
    from preflight.report import Report      # noqa: PLC0415

    mismatches = 0
    for art_name, stmt_name, want_pass in CASES:
        art = (ART / art_name).read_text(encoding="utf-8")
        stmt = (REF / "statements" / stmt_name).read_text(encoding="utf-8")
        rep = Report(str(ART / art_name), str(REF / "statements" / stmt_name))
        _static_checks(rep, art, stmt, Policy())
        got = rep.passed
        state = "pass" if got else "fail"
        mark = "ok  " if got == want_pass else "FAIL"
        if got != want_pass:
            mismatches += 1
            failures.append(f"{art_name}: expected {'pass' if want_pass else 'fail'}, got {state}")
        print(f"  {mark} {art_name:<38} -> {state}")
    return mismatches


def test_with_lean(lean: str) -> None:
    print(f"compile stage with {lean}")
    from preflight.compile import run as compile_run             # noqa: PLC0415
    from preflight.toolchain import Toolchain                    # noqa: PLC0415
    import os                                                    # noqa: PLC0415

    tc = Toolchain(lean, dict(os.environ))
    pairs = [
        ("add-zero.proof.lean", "add-zero.lean", "statementProp"),
        ("add-comm.proof.lean", "add-comm.lean", "statementProp"),
        ("false-claim-succ.refutation.lean", "false-claim-succ.lean", "¬statementProp"),
        ("false-claim-lt.refutation.lean", "false-claim-lt.lean", "¬statementProp"),
    ]
    for proof_name, stmt_name, expected_type in pairs:
        proof = (REF / "proofs" / proof_name).read_text(encoding="utf-8")
        stmt = (REF / "statements" / stmt_name).read_text(encoding="utf-8")
        src = compose(stmt, proof, extra_probes="#print axioms proof\n#check proof").source
        res = compile_run(tc, src, timeout=300)
        ok = res.ok and expected_type.replace(" ", "") in res.entry_type.replace(" ", "")
        expect(ok, f"{proof_name}: {res.summary()}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--with-lean", help="path to a lean binary; adds compile tests")
    args = ap.parse_args()

    test_scanner()
    test_composition()
    test_allowlist_and_axioms()
    test_cases()
    if args.with_lean:
        test_with_lean(args.with_lean)

    print()
    if failures:
        print(f"{len(failures)} failure(s):")
        for f in failures:
            print("  -", f)
        return 1
    print("all expectations met")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
