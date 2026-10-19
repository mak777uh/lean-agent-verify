# Reference set

Four (statement, artifact) pairs that pin down what the two settlement directions
look like. These are self-contained Lean - no Mathlib, no imports - so they check
the composition and the entry-theorem contract with nothing else in the way.

| statement | artifact | direction | expected |
|---|---|---|---|
| `statements/add-zero.lean` (`∀ n, n + 0 = n`) | `proofs/add-zero.proof.lean` | proved | `proof : statementProp` |
| `statements/add-comm.lean` (`∀ a b, a + b = b + a`) | `proofs/add-comm.proof.lean` | proved | `proof : statementProp` |
| `statements/false-claim-succ.lean` (`∀ n, n + 1 = n`) | `proofs/false-claim-succ.refutation.lean` | **disproved** | `proof : ¬statementProp` |
| `statements/false-claim-lt.lean` (`∀ n, n < n`) | `proofs/false-claim-lt.refutation.lean` | **disproved** | `proof : ¬statementProp` |

Artifacts contain **the theorem only**: the checker prepends the statement, so a
matching `def statementProp` in the artifact would be rejected as a redeclaration.

A disproof is payable on the same terms as a proof - the two false claims above
exist to keep that path exercised, because a checker can be wrong in either
direction.

Run them:

```bash
python tests/run_tests.py --with-lean /path/to/pinned/lean
```
