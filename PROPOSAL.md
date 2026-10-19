Developer Tooling Grant Proposal
Solana Foundation — lean-agent-verify

1. Applicant Information

Project / Tool Name
lean-agent-verify — reproducible Lean 4 verification pipeline for autonomous agents

Applicant / Organization
Individual applicant (no legal entity): an autonomous AI-agent team operating under a human operator. The operator approves every external action and holds all keys; the agents build and maintain the artifacts.

Location
Russia. We understand this may be a compliance restriction; we would rather know now than after review.

Primary Contact
Ilya Vladimirov — mak777777uh+agent@gmail.com — email only

Total Amount Requested (USD)
12,000

Relevant Experience & Track Record
We are a working Lean 4 pipeline, not a proposal for one. Current state, reproducible today:

- Pinned environment: Lean v4.36.0-rc1, Mathlib revision 9c6a29e8, lake build → 18,134 jobs, exit 0; lean-toolchain and lake-manifest.json are kept per run.
- Axiom discipline: #print axioms gated to the three standard kernel axioms (propext, Classical.choice, Quot.sound); no user axioms, no sorryAx. A public run log from a paid task shows exit=0 with exactly that axiom set.
- Machine-checked refutations: two compiling ¬ statementProp artifacts in full Mathlib, plus a core-only (import Std) variant for minimal-dependency policies.
- Paid-work experience on agent venues that verify Lean artifacts by static scan before compiling, and an EVM project (Mezo testnet) that reached Sourcify exact_match.
- Two documented failures that motivate this tool, both measured on our own losses (see section 2).

What we do not have, stated plainly: no PhD, no publications, no legal entity, and no prior grant. What we can show instead is a pipeline that runs daily and case files with the venues' own error text.

2. Overview of Ecosystem Impact

How is this project a public good for the Solana community?
Agents now earn on Solana rails by formalizing mathematics in Lean 4, and the venues that pay them verify artifacts through two gates that are invisible until after the agent has already spent money: a static token scan that runs before compilation, and a build environment that moves under the artifact. Neither gate ships a client-side checker, so every agent pays to rediscover the same two failures. This project is the missing client-side half of that loop, released open source with a reference corpus so any agent or developer can check an artifact before spending SOL.

Specific benefits to Solana developers
- A pre-flight scan that reproduces venue token policies locally, in under a second, before a transaction is signed.
- A provenance manifest format that makes "the same artifact, the same pin, the same result" a checkable claim instead of a memory.
- An axiom-hygiene gate that turns "no sorry, no smuggled axioms" into a pass/fail record rather than a reviewer's impression.
- A reference corpus (25 true statements, 5 false statements with compiling refutations) that any tool can be tested against, and that Solana venues can adopt as a compatibility test.
- Two public case files explaining the exact failure modes, with the venues' error text — useful even to teams that never run our code.

Measured motivation (from our own work, this week)
1. A paid Lean task on swarm.tips (Solana mainnet) was rejected before compilation: "proof contains forbidden token 'scoped'". The token came from an open scoped line that was not needed. We spent 0.00111744 SOL (0.00111244 claim + 0.000005 submit) and received no compiler output. The corrected artifact, byte-identical minus that line, built with exit=0 and the standard axiom set.
2. In the same pipeline, a cold run of an identical artifact in an identical pin took 433.9 s against 39.1 s on a warm cache — 5.4 GB of Mathlib olean cache evicted after parallel builds — with the verifier's limit at 600 s. The proof was unchanged; the instrument was not.

3. Product Design

Architecture & how it works
A small Python pipeline, no daemon and no network dependency at run time:

artifact.lean → token pre-flight → pinned build (lake env lean)
                        ↓                    ↓
                 policy report        axiom gate (#print axioms)
                        ↓                    ↓
                 provenance manifest (JSON, sha256)
                        ↓
                 verifier: same manifest from a clean run?

- Token pre-flight: reads the artifact bytes, applies the venue's token policy, reports every hit with line and byte offset, and refuses to send. Policies are data files, so a new venue is a new file.
- Pinned build: lake env lean inside the pinned toolchain; the pin is lean-toolchain + lake-manifest.json, never "latest".
- Axiom gate: parses #print axioms output for the entry theorem, compares the set to the three kernel axioms, and records pass/fail per theorem.
- Manifest: hashes of source, toolchain file, manifest file, and the emitted verdict; a verifier re-runs and compares byte-for-byte.

Key features
1. Sub-second token scan with a per-venue policy file and a 40-artifact calibration corpus.
2. Byte-identical manifest reproduction across a clean container and a warm cache.
3. Axiom gate with explicit sorryAx and imported-axiom handling.
4. Counterexample generator: for a false statement, emits a compiling ¬ statementProp with the same checks applied.
5. Machine-readable output (JSON) so a venue, an agent or CI can gate on it.

Integration into existing developer workflows
- CLI: python -m pipeline.check artifact.lean --policy <venue> returns exit 0/1 and a JSON report — usable as a git pre-commit hook.
- CI: a GitHub Action runs the full pipeline on every PR in under 10 minutes on the reference corpus.
- Venues: consume the manifest format directly to reject an artifact without compiling it, or to accept a cached verdict.

Technology stack
Python 3.11 (stdlib only for the scanner and manifest), Lean 4 (v4.36.0-rc1) + Mathlib for building, lake for the toolchain, GitHub Actions for CI. No hosted service, no database, no paid dependency.

Proof-of-Concept
Repository: https://github.com/mak777uh/lean-agent-verify — public, Apache-2.0, and the reference corpus ships with it. Two artifacts open right now: the rejected byte sequence (https://paste.rs/LORzk) and an axiom-gate run log showing exit=0 with only the kernel axioms (https://paste.rs/urPbZ).

4. Budget Breakdown (Milestones)

Total requested: 12,000 USD. Split as the template requires: per-component beta, six months of maintenance, and adoption metrics.

4a. Completed First Version (Beta) — per component

1. Pinned runner + provenance manifest — 2,200 USD
Beta scope: runs the reference corpus, emits and re-verifies a byte-identical manifest.
Testing plan: clean-container reproduction on two machines; 25/25 statements build exit=0.

2. Axiom-hygiene gate — 1,200 USD
Beta scope: #print axioms parsed per theorem, pass/fail recorded, sorryAx and imported axioms handled.
Testing plan: 3 deliberately broken artifacts (sorryAx, custom axiom, missing import) must be rejected 3/3.

3. Forbidden-token pre-flight scanner — 3,000 USD
Beta scope: per-venue policy files, 40-artifact calibration corpus, sub-second scan.
Testing plan: agreement with real venue verdicts ≥38/40; zero false positives on the 20 accepted artifacts.

4. Counterexample generator + reference set — 1,600 USD
Beta scope: for 5 false statements, emits compiling ¬ statementProp with axiom records.
Testing plan: 5/5 compile exit=0, axiom-clean, byte-stable across runs.

Beta subtotal: 8,000 USD

4b. Maintenance — minimum 6 months
6 × 400 USD/month = 2,400 USD. Each month is one milestone, paid as its own portion. Maintenance includes: issue triage and bug fixes to the Foundation's satisfaction, dependency pin updates (Lean/Mathlib bumps re-tested against the reference corpus), CI upkeep, and one release per month with notes. Scope excludes new components.

4c. User Adoption
- Repositories running the pipeline (pre-commit or CI): target ≥ 25 — tracked via GitHub Action usage counts plus a public self-registration file in the repo — 800 USD.
- Venues/teams referencing the manifest format or the scanner in their pre-submission check: target ≥ 3 — tracked via public issues/PRs in their repositories, linked from ours — 600 USD.
- Third-party reference-corpus runs recorded: target ≥ 100 — tracked in a public results file appended by the verifier (commit history is the audit trail) — 200 USD.

Adoption subtotal: 1,600 USD

Each metric is its own milestone; every 25% of a metric reached pays 25% of that metric's amount at period end.

Milestone Summary

1. Beta — pinned runner + manifest. Success: 25/25 reference statements exit=0; manifest byte-identical on a clean container. Amount: 2,200 USD.
2. Beta — axiom gate. Success: 3/3 broken artifacts rejected with the correct reason. Amount: 1,200 USD.
3. Beta — token scanner. Success: ≥38/40 agreement with venue verdicts; 0 false positives. Amount: 3,000 USD.
4. Beta — counterexample generator. Success: 5/5 false statements refuted with compiling artifacts. Amount: 1,600 USD.
5. Maintenance, months 1–6. Success: monthly release; issues closed to the Foundation's satisfaction. Amount: 2,400 USD.
6. Adoption metrics. Success: 25 repositories, 3 venue references, 100 corpus runs. Amount: 1,600 USD.

Total: 12,000 USD

Smaller check, if preferred: components 1 and 3, the mandated six months of maintenance, and reduced adoption (5 repositories, 1 venue reference) for 8,000 USD — same template, smaller scope, no dropped requirement.

5. Acknowledgements

✔ The project will release a published production version by the end of the grant agreement.
✔ The project will be completely public and open-source (Apache-2.0).
✔ The team agrees to at least 6 months of maintenance.
✔ The team agrees to meet quantifiable user-adoption metrics.

Payment: 4FRRxTQZgsv2X3dB76j1CS4UVUJD6b63czsmdLXbvYe4 (Solana) — USDC on Solana preferred, SOL acceptable. We accept payment through whichever programme the Foundation uses; KYC at payout on request, not at application stage.
