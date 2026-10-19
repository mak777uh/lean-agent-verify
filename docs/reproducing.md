# Reproducing a checker environment locally

`preflight` deliberately contains no paths and no versions of its own: a *policy*
describes the checker (toolchain, pinned Mathlib, allowlists, budget), and an
*environment file* points at a Lean installation. Both are inputs.

## 1. A policy file

```json
{
  "toolchain": "leanprover/lean4:v4.30.0",
  "mathlib_rev": "<40-hex commit>",
  "statement_def": "statementProp",
  "entry_theorem": "proof",
  "axiom_allowlist": ["propext", "Classical.choice", "Quot.sound"],
  "import_allowlist": ["Mathlib"],
  "reject_sorry": true,
  "max_build_secs": 600,
  "max_artifact_bytes": 5242880
}
```

Policies of this shape are published by bounty platforms as JSON; use the one
that matches the bounty you are submitting to. `python -m preflight policy
--policy my.json` prints what will actually be enforced.

## 2. An environment file

The environment only has to describe where Lean and the pinned library oleans
live. `lake env` emits exactly that; capture it once:

```bash
# inside a project whose lakefile pins the target toolchain + Mathlib
lake env pwsh -NoProfile -Command 'Get-ChildItem Env: | % { $_.Name + "=" + $_.Value }' > lean-env.txt
# or, on POSIX: env > lean-env.txt
```

`preflight/toolchain.py` keeps `LEAN_PATH`, `LEAN_SRC_PATH`, `LEAN_SYSROOT`,
`LAKE_HOME` and `PATH` from that file and inherits the rest of the process
environment.

If you only need the static gates (tokens, structure, imports), skip all of this:
those checks take milliseconds and no toolchain.

## 3. Building the pinned environment from scratch (what actually worked)

The awkward parts, in the order they bite:

1. **Toolchain download host may be blocked.** If `elan` cannot reach the
   release host, download the release archive from the project's GitHub releases
   directly and unpack it into `~/.elan/toolchains/<owner>--<repo>---<version>/`.
   A `.tar.zst` release supports HTTP range requests, so parallel ranges turn a
   30 KB/s single stream into something usable.
2. **A full-history clone is not needed.** Fetch the pinned Mathlib as an archive
   snapshot of the exact commit (`codeload.github.com/<repo>/tar.gz/<rev>`).
3. **Dependencies: keep the versions, lose the git requirement.** Lake wants git
   packages; for a throwaway verification tree it is enough to place each
   dependency snapshot beside Mathlib and rewrite the `require … @ git` lines to
   `require <name> from "../<name>"`. Do this **only** while resolving packages —
   see (5).
4. **Oleans: use the official cache.** `lake exe cache get` downloads prebuilt
   build artifacts for the pinned commit. It derives everything from `LEAN_PATH`
   / `LEAN_SRC_PATH`, so it also runs standalone once the packages are laid out.
5. **The cache key includes three file hashes.** Mathlib's cache is keyed on the
   *content* of `lakefile.lean`, `lean-toolchain` and `lake-manifest.json` plus
   `Lean.githash`. Any edit to those three (including a `require` rewrite) makes
   every lookup miss. Restore them byte-for-byte before fetching, and verify with
   `sha256`.
6. **Missing modules after a partial cache run** can be filled by compiling the
   identical sources with the same toolchain into the same olean tree; nothing
   about the proof changes.

## 4. Running the checks

```bash
python -m preflight check my-artifact.lean my-statement.lean \
    --policy policy.json --lean-env lean-env.txt --json
```

Exit code 0 means every gate passed (static + compile + axioms + entry-theorem
type). Non-zero means do not submit.

## 5. What "reproducible" means here and what it does not

Loops back on purpose: the environment you build locally is only *equivalent* to
the checker's if the versions match. Keep the policy's toolchain id, Mathlib
commit and axiom allowlist, and record the content fingerprints of every package
tree you used, so a disagreement can be argued with hashes instead of memory.
