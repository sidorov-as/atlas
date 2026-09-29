## Why

A prerelease audit found the Python codebase does not pass its own declared Ruff configuration: 2402 violations across the 10 Python packages (`core/backend`, `plugin-api/python`, and the 8 plugin backends). A public open-source project should not ship a linter config it cannot satisfy — it undermines trust before anyone reads a line of application code, and one violation class (`RUF012` mutable-class-default) is a latent shared-mutable-state bug, not just style noise.

This change is deliberately sequenced first among the prerelease-hardening batch (`fix-ingestion-path-traversal`, `add-safe-http-helper`, `fix-apis-ssrf`, `fix-auth-dns-rebinding`, `fix-production-fail-closed-config`, `harden-input-field-limits`): it touches nearly every Python file, so landing it before those changes avoids lint-formatting churn colliding with their diffs.

## What Changes

- Reformat all Python source to satisfy each package's own `pyproject.toml` Ruff config (line length, import ordering) — dominated by `E501` line-too-long (~88% of violations sampled), which is not fixed by `ruff --fix` and requires actual reflow of long lines (docstrings, comments, call chains).
- Fix `RUF012` (mutable-class-default) occurrences as real bug fixes: for each, verify whether the code actually relied on the mutable default being shared across instances before changing it to a per-instance default (e.g. `field(default_factory=...)` or `None`-then-initialize), not a blind suppression.
- Apply safe auto-fixes: `I001` (unsorted imports), `RUF100` (unused `noqa`), and the remaining mechanical rules (`FURB188`, `RUF022`, `TC005`).
- Fix the small number of remaining manual-judgment violations (`SIM117`, `PYI034`, `EXE002`, `PLW1510`, `TRY004`) one at a time, on their own merits.
- Add `ruff check` (and `ruff format --check` if not already run) as a required, blocking step for each Python package — this is scoped only to making the *current* codebase pass; wiring it into a shared/expanded CI workflow is `harden-ci-and-supply-chain`'s job, not this change's.
- No behavior change anywhere else: this is formatting, import order, and the specific `RUF012` correctness fixes — no new features, no API changes.

## Capabilities

### New Capabilities

None — this is internal code quality, not user-facing behavior.

### Modified Capabilities

- `backend-platform-foundation`: The existing "Quality tooling is introduced without blocking remediation" requirement documents Ruff findings as tracked, bounded follow-up debt rather than a blocking gate. This change closes that debt for the current codebase: Ruff findings across all Python packages are resolved rather than merely recorded, and the requirement is updated to reflect a clean, verifiable baseline instead of an open backlog. (If any `RUF012` fix turns out to require a behavior change beyond "stop sharing mutable state across instances," that finding should be split into its own change rather than folded in here.)

## Impact

- Touches Python source files across `core/backend/`, `plugin-api/python/`, and all 8 plugin backends under `plugins/*/backend/`.
- No runtime dependency changes expected.
- No database, API, or schema changes.
- Downstream: unblocks the prerelease-hardening batch to branch from a lint-clean baseline.
