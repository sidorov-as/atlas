## Context

Repo root currently has `LICENSE` only. `.github/` has `workflows/` and `actions/` but no `ISSUE_TEMPLATE/` or `PULL_REQUEST_TEMPLATE.md` (confirmed by directory listing). No `SECURITY.md`, `CONTRIBUTING.md`, or `CODE_OF_CONDUCT.md` exist anywhere in the repo. This change is pure documentation/process, part of the same prerelease-readiness batch as the security-fix changes but with zero code overlap or ordering dependency on any of them.

## Goals / Non-Goals

**Goals:**
- A credible, findable private vulnerability-disclosure path exists before the project is public.
- Standard GitHub community-health files are present so the repo reads as an intentionally-maintained open-source project, not an abandoned dump.
- Issue/PR templates nudge external contributors toward the information maintainers actually need.

**Non-Goals:**
- Standing up the actual disclosure inbox/process infrastructure (e.g. a dedicated security email alias, GitHub Security Advisories configuration) — that's an operational decision for the project owner, not something this change can implement blind. This change specifies what `SECURITY.md` should say once that decision is made, and flags it as an open question.
- Any code, workflow, or CI change — those are covered by sibling changes in this batch (`harden-ci-and-supply-chain`, etc.), not here.
- A full CLA or governance model (maintainer list, decision-making process) — out of scope unless the project owner asks for it later.

## Decisions

- **New capability (`community-health-files`) rather than folding into `documentation-site-experience`.** That capability is specifically the in-product documentation site (the docs-site experience end users get inside Atlas), not repo-root GitHub metadata read by external contributors before they ever run the product. Conflating the two would misrepresent what each capability actually governs.
- **`SECURITY.md` content is specified, but the disclosure contact is a placeholder pending owner decision.** Inventing a fake email address or asserting GitHub Security Advisories is configured would be worse than flagging the gap — a non-functional disclosure channel is worse than an honest "ask the maintainer" placeholder, since a researcher who hits a dead end may default to public disclosure instead.
- **`CONTRIBUTING.md` should mention the project's own OpenSpec-based planning workflow** (proposal → design → specs → tasks under `openspec/changes/`), since that's a real, distinctive part of how changes get made here, not a generic "open a PR" boilerplate.

## Risks / Trade-offs

- **Placeholder disclosure contact ships if this change is implemented before the owner decides** → mitigate by making the task list's first item literally "get the disclosure contact mechanism from the project owner," blocking the `SECURITY.md` content task until that's answered, rather than let a placeholder slip into a real file.
- **Templates can feel like process theater if unmaintained** → keep issue/PR templates short and genuinely useful (repro steps, environment) rather than exhaustive forms nobody fills in.

## Open Questions

- What email address, form, or mechanism should `SECURITY.md` point to for private vulnerability reports? (GitHub Security Advisories' private reporting feature is a reasonable default if the project owner has no existing security contact, but confirm before implementing.)
- Does the project want a defined supported-versions table (e.g. "only latest tagged release"), or is "main branch only, no version support commitment yet" accurate for a prerelease project? Given there are no tags yet (per the audit's history findings), the latter is likely correct until a `v0.1.0` release exists.
