## Context

Reading `.github/workflows/*.yml` directly (not relying on the audit's summary) confirms the current state:

- `authentication-examples-fast.yml`: validates the authentication-examples fixtures/docs/compose rendering — not general backend correctness.
- `authentication-examples-integration.yml`: runs Docker-based integration smoke tests for auth examples, plus a *named list* of nine specific security-negative pytest cases — not the full backend suite.
- `migration-lint.yml`: blocks destructive migrations and checks cross-plugin migration dependency boundaries — narrow and unrelated to general test/lint coverage.
- `pages.yml`: builds and deploys the docs site.

None of these run the full backend test suite, any frontend test/build/lint step, Ruff, `npm audit`, `pip-audit`, or a secret scanner. No `.github/dependabot.yml` exists. Every action reference across all four workflows and the one composite action (`setup-python-env`) uses a mutable tag.

## Goals / Non-Goals

**Goals:**
- Every merge to `main` (and every PR) is gated by: full backend pytest, frontend test/build/lint, Ruff (per package), `npm audit --audit-level=high`, `pip-audit`, and a secret scan.
- The CI definition itself doesn't trust mutable upstream references — every third-party action is pinned to a commit SHA, with automated pin-bump PRs so pins don't silently rot.
- New required checks are introduced without a "day one" CI outage caused by pre-existing red state elsewhere in the codebase.

**Non-Goals:**
- Fixing the Ruff violations, frontend dependency vulnerabilities, or any backend test failures themselves — those are `ruff-cleanup` and `fix-frontend-dependency-vulnerabilities`'s job. This change only adds the gate.
- Restructuring the existing four workflows' own logic (auth-examples validation, migration lint, docs deploy) beyond pinning their action references.
- Choosing a specific secret-scanning SaaS/vendor beyond Gitleaks (already the tool the audit used manually, so it's the natural choice — but the exact invocation, e.g. GitHub Action vs. CLI step, is an implementation detail for tasks.md).

## Decisions

- **Sequencing: ship new gates as blocking checks, but land this change after `ruff-cleanup` and `fix-frontend-dependency-vulnerabilities`, rather than shipping them non-blocking first.** Two options were considered:
  - (a) Merge this change last, once the Python codebase is Ruff-clean and frontend vulnerabilities/tests are fixed — the new "required" checks are green from the moment they exist.
  - (b) Merge this change any time, with the new checks initially non-blocking/reporting-only, then flip them to required in a fast-follow once green.
  - Chosen: (a). Option (b) means there's a window where a "required" CI badge exists but isn't actually enforced, which is exactly the kind of gap this change exists to close — and it adds a second PR (the "flip to required" follow-up) that's easy to forget. Landing last costs nothing extra since this change has no code dependencies on the others (it only touches `.github/`), and the batch is already being sequenced deliberately (`ruff-cleanup` lands first as a baseline; this is a natural place to land last).
- **New capability, not a delta on an existing one.** `backend-platform-foundation` and `deployment-manifest-and-lock` both describe the *application's* runtime/deployment behavior, not the CI process that verifies changes to it — conflating them would make an unrelated capability's spec describe process rather than product behavior.
- **Pin to commit SHA with a version comment, not a floating major-version range.** SHA pinning is the only form that actually prevents a re-tagged or compromised release from silently changing CI behavior; a comment (`# v4.2.1`) keeps it human-reviewable without reintroducing the mutable-tag risk.
- **Gitleaks as a new CI job, not a tightening of an existing one.** Nothing in the current workflows runs it; the audit's Gitleaks pass was a manual one-off check.

## Risks / Trade-offs

- **Pinning to SHA increases workflow-file churn** (a version bump now means a new SHA line, not just a tag edit) → mitigated by Dependabot/Renovate opening the bump PRs automatically, so it's a review-and-merge, not manual lookup.
- **Full backend pytest across every plugin may be slow** compared to today's narrow security-negative subset → acceptable trade-off for actually gating correctness; can be parallelized by plugin in a matrix job if runtime becomes a problem (implementation detail for tasks.md).
- **Landing last means this change is idle/blocked on other people's work** → acceptable since it has no code dependency, only a merge-order dependency; it can be fully drafted and reviewed in parallel, just not merged first.
- **Secret scanning on full history vs. diff-only** → scanning every PR's diff is cheap and continuous; a periodic full-history scan (like the audit's one-off 49-commit pass) is a separate, heavier job this change does not mandate but doesn't preclude adding later.

## Migration Plan

1. Add the Dependabot/Renovate config for GitHub Actions.
2. Pin all existing action references (four workflows + the one composite action) to commit SHA.
3. Add the new backend-pytest, frontend-checks, Ruff, dependency-audit, and secret-scan workflows.
4. Confirm `ruff-cleanup` and `fix-frontend-dependency-vulnerabilities` have merged (or merge this change after them).
5. Mark the new workflows as required status checks on the default branch's protection rules (repo setting, not a file in this repo — note as a manual step in tasks.md).

No rollback complexity beyond reverting the workflow files / branch-protection setting; no runtime or data impact.

## Open Questions

- Exact job/matrix structure for running per-plugin backend pytest (one job per plugin vs. a single matrix job) — left to tasks.md/implementation judgment.
- Whether Dependabot should also be extended to npm/pip package ecosystems in this change or left to a future change — out of scope here (this change's Dependabot config is GitHub-Actions-only); flag for follow-up if desired.
