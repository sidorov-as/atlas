## 1. Resolve open questions

- [x] 1.1 Get the disclosure contact mechanism (email, form, or GitHub Security Advisories) from the project owner — do not proceed to 2.1 with a placeholder.
- [x] 1.2 Confirm the supported-versions statement (likely "main branch only, pending first tagged release" until `v0.1.0` exists).

## 2. Security policy

- [x] 2.1 Write `SECURITY.md` with the confirmed disclosure channel and supported-versions statement.

## 3. Contribution guidance

- [x] 3.1 Write `CONTRIBUTING.md`, including dev setup pointers and this project's OpenSpec-based planning workflow (proposal → design → specs → tasks under `openspec/changes/`).
- [x] 3.2 Write `CODE_OF_CONDUCT.md` (e.g. adapt the Contributor Covenant).

## 4. Templates

- [x] 4.1 Add `.github/ISSUE_TEMPLATE/bug_report.md`.
- [x] 4.2 Add `.github/ISSUE_TEMPLATE/feature_request.md`.
- [x] 4.3 Add `.github/PULL_REQUEST_TEMPLATE.md`.

## 5. Verification

- [x] 5.1 Confirm all new files render correctly on GitHub (templates show up in the "new issue"/"new PR" flows once pushed). *(Verified locally: valid YAML front matter on both issue templates, correct relative links to `SECURITY.md`/`CONTRIBUTING.md`; not verified live on GitHub since the branch wasn't pushed — spot-check after pushing.)*
- [x] 5.2 Cross-link: `SECURITY.md` mentions `CONTRIBUTING.md`'s process where relevant, and vice versa, so a reader landing on either finds the other.
