## Context

`atlas-compose resolve` writes `hash: sha256:…` for each backend artifact and `integrity: sha512-…` for each frontend artifact. Registry packages reuse the value from `uv.lock` or `package-lock.json`. Workspace packages, which are every plugin today, get a value computed by `_hashing.hash_directory` over the package's git-listed files.

No consumer reads these fields. `lock.py` parses them into the model and that is all: `validate`, `generate`, the Dockerfiles (`uv sync --frozen`, `npm ci`) and CI ignore them. The original design said the lock should be a thin layer over native locks and not re-derive hashes; the directory hashing for workspace packages departs from that. Because the hash depends on file contents, any edit under `plugins/` changes every `lock.yaml` that includes the plugin.

Constraints: the lock is also the input to `generate`, so version, package, disabled state, config, services and authentication data must stay.

## Goals / Non-Goals

**Goals:**
- Remove fields and code that have no consumer.
- Make `lock.yaml` change only when manifest, native locks, or composer behaviour change.
- Keep the lock-from-manifest staleness check cheap and enforced in CI.

**Non-Goals:**
- Verifying artifacts during build. `uv sync --frozen` and `npm ci` already do this for the native locks.
- Supporting non-workspace artifact sources, or changing how the native locks are read for versions.
- Designing integrity for third-party plugin delivery. If that arrives it should be designed against a concrete delivery mechanism.

## Decisions

**1. Remove the fields entirely, rather than keep registry hashes and drop only workspace hashes.**
Alternatives: (a) keep both and add verification, (b) keep registry values and drop workspace values, (c) remove both. Option (a) adds a check that guards nothing in a monorepo, since code and lock arrive in one commit. Option (b) leaves fields that are optional by source, which complicates the schema and still has no reader, and the native locks keep the same values. Option (c) gives one schema and one source of truth for integrity. Chosen: (c).

**2. Reject locks that still carry the old fields, rather than ignore them.**
The lock model already uses `extra="forbid"`. Keeping that means a stale lock fails loudly with a message to re-resolve, instead of silently carrying dead data. Alternative: accept and drop legacy fields, which hides drift and leaves old files in the repo. Rejected, since every in-repo lock is regenerated in this change.

**3. Keep reading `uv.lock` and `package-lock.json`, but only for version and existence.**
`_resolve_backend` and `_resolve_frontend` still need the exact version and the mismatch check. `uv_lock.py` and `npm_lock.py` shrink to name→version maps. The path-based fallback for packages missing from `uv.lock` stays, minus the hash.

**4. Delete `_hashing.py` and its test.**
Its only callers are the three resolution paths above. Alternative: keep it for later use. Rejected, since unused code with git and subprocess calls is a cost and can be restored from history.

**5. Add a CI freshness check: re-resolve all distributions, fail on `git diff`.**
Alternatives: (a) no check, (b) a `verify` command that compares hashes, (c) re-resolve and diff. Without hashes, the staleness that matters is manifest or native-lock changes not reflected in the lock. Option (c) catches that with the existing `make lock`, with no new composer command. It becomes practical now because unrelated source edits no longer alter the output.

## Risks / Trade-offs

- [Operators with tooling that reads `hash` or `integrity` from `lock.yaml`] → none known in this repository; recorded as BREAKING in the proposal, and the load error explains how to regenerate.
- [Loss of an integrity field that could have supported third-party plugins] → native locks already provide it for registry artifacts; revisit with a real delivery mechanism.
- [CI check needs the toolchain used by `make lock`] → reuse the `uv run --project composer` invocation the Makefile already defines.

## Migration Plan

1. Change schema, resolver and native-lock readers; delete the hashing helper.
2. Run `make lock` to regenerate every `lock.yaml`.
3. Update docs and tests, then add the CI step.

Rollback: revert the commit; the previous lock files and code return together.
