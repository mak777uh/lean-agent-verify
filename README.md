# lean-agent-verify

Local pre-flight checks for **Lean proof-bounty artifacts**: the three gates a
submission has to pass, checked in seconds instead of after a paid round-trip.

A proof bounty pays only when the checker accepts the artifact. In practice a
submission is rejected for reasons that have nothing to do with the mathematics:

| gate | what goes wrong | caught by |
|---|---|---|
| static policy | a meta-command token in the artifact source (`scoped`, `namespace`, `axiom`, `sorry`, `run_tac`, …) — rejected **before** Lean runs | `preflight/tokens.py` |
| structure | the artifact redeclares the campaign's statement, or has no entry theorem | `preflight/compose.py` |
| mathematics | the proof does not elaborate on the *pinned* toolchain, or exceeds the build budget | `preflight/compile.py` |
| dependency hygiene | the entry theorem depends on an axiom outside the allowlist (`sorryAx`, `Lean.ofReduceBool`, …) | `preflight/compile.py` + `Policy.axiom_allowlist` |

The first, second and fourth gates are cheap and are where bounties actually die.
This package exists because one did: a correct refutation, verified on the exact
pinned toolchain with the exact allowed axioms, was rejected for containing
`open scoped BigOperators` and cost a claim fee — see
[`incidents/`](incidents/2026-10-19T175212Z-scoped-token.md).

## Quick start

```bash
# static only: no Lean, no toolchain, milliseconds
python -m preflight check my-artifact.lean my-statement.lean --no-compile

# full: needs a Lean binary and (for a Mathlib policy) a captured environment
python -m preflight check my-artifact.lean my-statement.lean \
    --policy policy.json --lean-env lean-env.txt --json
```

Exit code `0` = safe to submit. Non-zero = do not submit.

```bash
python -m preflight tokens            # the forbidden-token table, with provenance
python -m preflight policy --policy p.json
python tests/run_tests.py             # ~0.2 s, no toolchain needed
```

## What a check does, in order

1. **Artifact size** against the policy's limit.
2. **Forbidden tokens** — the artifact's own source, comments stripped (nested
   Lean block comments handled). Each token in the table records whether it was
   *observed* being rejected or *inferred* from a "no meta commands" rule.
3. **Statement not redeclared** — the checker prepends the campaign statement, so
   redeclaration scores zero.
4. **Entry theorem present** (`proof` by default).
5. **Imports** — the artifact's own `import` lines must sit inside the policy
   allowlist. The artifact usually has to carry them: campaign statements import a
   narrow subset, and without the tactics/algebra modules a proof cannot elaborate.
6. **Composition** — statement prepended, both sides' imports hoisted into one
   header, exactly as the checker assembles its compilation unit.
7. **Compile** on the pinned toolchain, inside the policy's wall-clock budget.
8. **Axioms** — `#print axioms proof` must be a subset of the allowlist.
9. **Direction** — `#check proof` must report `proof : statementProp` (proof) or
   `proof : ¬statementProp` (disproof); both directions are payable.

## Layout

```
preflight/      the library + CLI (stdlib only)
  policy.py     what the checker enforces (toolchain, allowlists, budget)
  tokens.py     static scan, with the incident behind each token
  compose.py    statement-prepended composition + import/allowlist rules
  toolchain.py  find Lean, load a captured `lake env` environment
  compile.py    elaborate, parse errors/axioms/entry-theorem type
  report.py     PASS/FAIL rendering, text or JSON
  cli.py        `check`, `tokens`, `policy`
reference/      4 statements + 4 artifacts: 2 proofs, 2 refutations (the known-good case)
incidents/      real rejections, with the raw checker reply and the cost
docs/           how to reproduce a pinned checker environment
tests/          artifact matrix (pass / scoped / sorry / axiom / redeclaration / no entry theorem)
```

## Design notes

* **No paths and no secrets in the code.** A policy file describes the checker; an
  environment file describes the toolchain. Both are user inputs.
* **Static checks never need Lean**, so they can run in CI on every commit.
* **The compiler is the checker, not a substitute for it.** The package mirrors the
  *documented and observed* assembly of the compilation unit; if a platform changes
  its composition rule, the reference matrix in `tests/` is where that shows up
  first.
* **Failure messages are the product.** Every FAIL says which gate, what was found,
  and (for tokens) why that token is rejected.

## Status

Early, honest scope: this catches the failure modes that were actually observed on
a live platform, not every conceivable one. Contributions that come with a real
rejection are the most valuable kind.
