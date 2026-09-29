## Why

A prerelease audit confirmed the repo has a `LICENSE` file but none of the standard community/security files an open-source project needs: no `SECURITY.md`, root `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, issue/PR templates, or supported-versions policy. This matters especially because the same audit found two real release-blocking vulnerabilities (arbitrary file read via ingestion, SSRF via API spec fetching) — a project that ships with security findings but no credible private-disclosure path sends a bad signal to anyone who finds the next one after release.

## What Changes

- Add `SECURITY.md` at the repo root describing supported versions and a private vulnerability-disclosure channel.
- Add root `CONTRIBUTING.md` describing how to propose changes (including this project's use of OpenSpec for planning, dev setup pointers, and PR expectations).
- Add `CODE_OF_CONDUCT.md`.
- Add `.github/ISSUE_TEMPLATE/` templates (bug report, feature request) and `.github/PULL_REQUEST_TEMPLATE.md`.
- Document a supported-versions policy (inside `SECURITY.md`).

This is documentation/process only — no application code, API, or runtime behavior changes.

## Capabilities

### New Capabilities

- `community-health-files`: The presence and minimum content of the repo's community/security governance files — `SECURITY.md` (with a private disclosure channel and supported-versions policy), `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, and issue/PR templates.

### Modified Capabilities

None.

## Impact

- Adds new root files: `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`.
- Adds new files under `.github/ISSUE_TEMPLATE/` and `.github/PULL_REQUEST_TEMPLATE.md`.
- No code, API, dependency, or runtime changes.
- Fully independent of every other prerelease change in this batch — no shared files, no ordering constraint.
- Open question (see design.md): the actual private-disclosure contact mechanism for `SECURITY.md` needs a decision from the project owner before this is implemented — this proposal does not invent one.
