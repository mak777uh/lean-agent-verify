"""Command line entry point: ``python -m preflight check <artifact> <statement>``.

Static checks always run; the compile stage runs when a Lean binary and (for a
Mathlib policy) a captured environment are available. Nothing here touches the
network, a wallet, or a bounty platform - it only decides whether a *local*
artifact is worth submitting.
"""
from __future__ import annotations

import argparse
import hashlib
import pathlib
import sys

from .compile import run as compile_run
from .compose import (check_import_allowlist, compose as compose_sources,
                      find_redeclarations)
from .policy import Policy
from .report import FAIL, OK, SKIP, Report
from .tokens import scan as scan_tokens, table as token_table
from .toolchain import resolve as resolve_toolchain, version as toolchain_version


def _static_checks(rep: Report, artifact: str, statement: str, policy: Policy) -> None:
    art_bytes = len(artifact.encode("utf-8"))
    if art_bytes > policy.max_artifact_bytes:
        rep.add("artifact size", FAIL,
                f"{art_bytes} bytes > policy limit {policy.max_artifact_bytes}")
    else:
        rep.add("artifact size", OK, f"{art_bytes} bytes")

    findings = scan_tokens(artifact)
    if findings:
        rep.add("forbidden tokens", FAIL, "; ".join(str(f) for f in findings[:6]))
    else:
        rep.add("forbidden tokens", OK, "no meta-command token in code")

    reserved = [policy.statement_def, "dyadicEnergy", "dyadicEnstrophy",
                "dyadicHelicalStretching"]
    redeclared = find_redeclarations(artifact, reserved)
    if redeclared:
        rep.add("statement not redeclared", FAIL,
                "artifact declares " + ", ".join(redeclared) +
                " (the checker prepends the statement; redeclaration scores 0)")
    else:
        rep.add("statement not redeclared", OK, "none of the campaign names redefined")

    if f"theorem {policy.entry_theorem}" in artifact or f"lemma {policy.entry_theorem}" in artifact:
        rep.add("entry theorem present", OK, f"`{policy.entry_theorem}` found")
    else:
        rep.add("entry theorem present", FAIL,
                f"no `theorem {policy.entry_theorem}` in the artifact")

    composed = compose_sources(statement, artifact)
    bad = check_import_allowlist(composed.imports, policy.allows_import)
    if bad:
        rep.add("import allowlist", FAIL, "disallowed: " + ", ".join(bad))
    else:
        rep.add("import allowlist", OK, composed.summary())

    rep.meta["imports"] = composed.imports
    rep.meta["artifact_sha256"] = hashlib.sha256(artifact.encode()).hexdigest()
    rep.meta["composed_chars"] = len(composed.source)


def _compile_checks(rep: Report, artifact: str, statement: str, policy: Policy,
                    lean: str | None, env_file: str | None, timeout: int) -> None:
    try:
        tc = resolve_toolchain(lean, env_file)
    except FileNotFoundError as exc:
        rep.add("compile on pinned toolchain", SKIP, str(exc))
        return

    composed = compose_sources(statement, artifact,
                                   extra_probes=f"#print axioms {policy.entry_theorem}\n"
                                                f"#check {policy.entry_theorem}")
    budget = min(timeout, policy.max_build_secs)
    result = compile_run(tc, composed.source, timeout=budget)
    rep.meta["toolchain"] = toolchain_version(tc)
    rep.meta["compile_seconds"] = round(result.seconds, 1)

    if result.timed_out:
        rep.add("compile on pinned toolchain", FAIL,
                f"timed out after {result.seconds:.0f}s (policy limit {policy.max_build_secs}s)")
    elif result.errors or result.exit_code != 0:
        rep.add("compile on pinned toolchain", FAIL,
                (result.errors[0] if result.errors else f"exit {result.exit_code}"))
    else:
        rep.add("compile on pinned toolchain", OK, f"{result.seconds:.0f}s")

    if result.timed_out or (result.errors and result.exit_code != 0):
        rep.add("axiom allowlist", SKIP, "compile failed")
        return

    extra = [a for a in result.axioms if a not in policy.axiom_allowlist]
    if extra:
        rep.add("axiom allowlist", FAIL,
                "axioms outside the allowlist: " + ", ".join(extra))
    else:
        rep.add("axiom allowlist", OK, "[" + ", ".join(result.axioms) + "]")

    if result.entry_type:
        rep.add("entry theorem type", OK, result.entry_type)
    else:
        rep.add("entry theorem type", FAIL, "checker did not report the theorem's type")


def cmd_check(args: argparse.Namespace) -> int:
    artifact_path = pathlib.Path(args.artifact)
    statement_path = pathlib.Path(args.statement)
    artifact = artifact_path.read_text(encoding="utf-8")
    statement = statement_path.read_text(encoding="utf-8")

    policy = Policy.from_json(args.policy) if args.policy else Policy()
    rep = Report(str(artifact_path), str(statement_path))
    _static_checks(rep, artifact, statement, policy)
    if args.no_compile:
        rep.add("compile on pinned toolchain", SKIP, "--no-compile")
    else:
        _compile_checks(rep, artifact, statement, policy,
                        args.lean, args.lean_env, args.timeout)

    print(rep.to_json() if args.json else rep.render())
    return 0 if rep.passed else 1


def cmd_tokens(_: argparse.Namespace) -> int:
    print(token_table())
    return 0


def cmd_policy(args: argparse.Namespace) -> int:
    p = Policy.from_json(args.policy) if args.policy else Policy()
    for field_name in Policy.__dataclass_fields__:
        print(f"{field_name:20} {getattr(p, field_name)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="preflight",
                                 description="Cheap checks before submitting a Lean proof-bounty artifact")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="scan + optionally compile an artifact against a statement")
    c.add_argument("artifact")
    c.add_argument("statement")
    c.add_argument("--policy", help="policy JSON (toolchain, allowlists, limits)")
    c.add_argument("--lean", help="path to the lean binary")
    c.add_argument("--lean-env", help="captured KEY=VALUE environment (from `lake env`)")
    c.add_argument("--timeout", type=int, default=900)
    c.add_argument("--no-compile", action="store_true", help="static checks only")
    c.add_argument("--json", action="store_true")
    c.set_defaults(func=cmd_check)

    t = sub.add_parser("tokens", help="print the forbidden-token table with provenance")
    t.set_defaults(func=cmd_tokens)

    p = sub.add_parser("policy", help="show the effective policy")
    p.add_argument("--policy")
    p.set_defaults(func=cmd_policy)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

