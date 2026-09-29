## Context

Each of the 10 Python packages (`core/backend`, `plugin-api/python`, and 8 plugin backends under `plugins/*/backend/`) ships its own `pyproject.toml` with its own Ruff configuration. A prerelease audit ran Ruff per-package and totaled 2402 violations; sampling one package's scope shows the dominant class is `E501` line-too-long (~88%), followed by `RUF012` mutable-class-default (65 in the sampled scope), `I001` unsorted-imports, `RUF100` unused-noqa, and a handful of one-off rules. This is prerelease polish work, not a response to a specific incident, but it is treated as a prerequisite gate: it deliberately lands before the prerelease security/hardening batch (`fix-ingestion-path-traversal`, `add-safe-http-helper`, `fix-apis-ssrf`, `fix-auth-dns-rebinding`, `fix-production-fail-closed-config`, `harden-input-field-limits`) so those changes branch from a lint-clean baseline instead of colliding with a broad reformat later.

## Goals / Non-Goals

**Goals:**
- `ruff check` passes with zero violations, per-package, using each package's existing declared configuration (not by loosening the configuration to make violations disappear).
- `RUF012` occurrences are fixed as correctness changes: each one gets a real look at whether instances were relying on the shared mutable class-level default, with a fix that removes the sharing (e.g. `dataclasses.field(default_factory=...)`, or initializing the container in `__init__`).
- The reformatting is a pure diff: no behavior change bundled in under cover of "cleanup."

**Non-Goals:**
- Wiring `ruff check` into CI as a required gate — that belongs to `harden-ci-and-supply-chain`, which needs to sequence it against when other gates (tests, npm audit, pip-audit, secret scan) go green too.
- Adjusting Ruff's rule selection or per-package config (e.g. raising `line-length` to make `E501` go away without reformatting) — that would be gaming the linter, not satisfying it, and works against the trust goal motivating this change.
- Any of the security or config-hardening fixes covered by the other prerelease changes — if a `RUF012` fix turns up a real behavior-affecting bug beyond "instances shared state," that finding gets split into its own change rather than folded in here.

## Decisions

- **Reformat by hand/tooling per violation class, not by relaxing config.** `ruff check --fix` only resolves `I001`, `RUF100`, and a few of the misc rules (59 of 1131 in the sampled scope); `E501` needs actual line reflow. Using `ruff format` first is acceptable where it closes gaps mechanically, but it doesn't guarantee zero `E501` (it won't break long strings/comments), so a manual pass is still needed afterward.
- **Fix `RUF012` before suppressing it.** A blanket `# noqa: RUF012` would satisfy the linter without addressing the underlying risk (mutable defaults shared across instances). Each occurrence needs a one-line judgment call: was anything actually relying on the sharing? If yes, that's worth flagging as its own finding rather than silently changing behavior.
- **Land this first, everything else branches after.** Chosen over doing it last (would force every security-fix branch to rebase through a late broad reformat) or doing it never (leaves the "trustworthy public codebase" goal unmet). See proposal.md for the parallelism rationale.
- **No CI wiring in this change.** Keeps this change's diff to "the codebase is clean" and lets `harden-ci-and-supply-chain` own the decision of when gates become required, since that decision depends on the state of changes outside this one's scope (frontend tests, npm audit, etc.).

## Risks / Trade-offs

- **Large diff, low review signal per line** → mitigate by keeping `RUF012` fixes in separate, clearly-labeled commits from pure reformatting, so a reviewer can scrutinize the handful of behavior-adjacent changes without wading through thousands of reflowed lines.
- **Landing first means it's rebased onto by six other changes** → if this change's PR sits open too long, it becomes a bottleneck instead of an accelerant. Mitigate by keeping scope strictly mechanical (no waiting on design debate) so it can merge quickly.
- **Reflowing long lines can accidentally change string content (e.g. a multi-line SQL or regex)** → mitigate with a diff review pass specifically for non-comment, non-docstring long lines, and running each package's existing test suite after reformatting.

## Migration Plan

1. Run `ruff format` per package where it reduces violations without behavior risk.
2. Manually reflow remaining `E501` lines package by package.
3. Fix each `RUF012` occurrence individually, verifying no reliance on shared state.
4. Apply remaining safe auto-fixes (`I001`, `RUF100`, `FURB188`, `RUF022`, `TC005`).
5. Resolve the last manual-judgment rules (`SIM117`, `PYI034`, `EXE002`, `PLW1510`, `TRY004`) individually.
6. Run each package's test suite to confirm no behavior change.
7. Confirm `ruff check` is clean per package.

No rollback complexity: this is a formatting/correctness change with no runtime migration, feature flag, or data implications.

## Open Questions

- None outstanding — scope and sequencing were settled in the prerelease-audit exploration this change originates from.
