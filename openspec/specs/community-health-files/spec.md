# community-health-files Specification

## Purpose

Defines the presence and minimum content of the repository's standard
community and security governance files: a private vulnerability-disclosure
path with supported-versions policy (`SECURITY.md`), contribution guidance
(`CONTRIBUTING.md`), a code of conduct (`CODE_OF_CONDUCT.md`), and GitHub
issue/PR templates under `.github/`. These files are documentation/process
only — they do not affect application code, APIs, or runtime behavior.

## Requirements

### Requirement: Private vulnerability disclosure path exists
The repository SHALL include a root `SECURITY.md` documenting a private
channel for reporting vulnerabilities and a supported-versions statement.

#### Scenario: Researcher finds SECURITY.md
- **WHEN** a security researcher looks for a disclosure process in the repository root
- **THEN** `SECURITY.md` exists and names a private reporting channel, not just "open a public issue"

#### Scenario: Supported versions are stated
- **WHEN** a reader checks `SECURITY.md` for which versions receive fixes
- **THEN** it states the current supported-versions policy (even if that policy is "main branch only, pending first tagged release")

### Requirement: Contribution guidance exists
The repository SHALL include a root `CONTRIBUTING.md` describing how to
propose and submit changes, including this project's OpenSpec-based planning
workflow.

#### Scenario: New contributor looks for guidance
- **WHEN** a contributor opens the repository root looking for how to contribute
- **THEN** `CONTRIBUTING.md` exists and describes the expected process, including where planning artifacts (`openspec/changes/`) fit in

### Requirement: Code of conduct exists
The repository SHALL include a root `CODE_OF_CONDUCT.md`.

#### Scenario: Community member checks conduct expectations
- **WHEN** a community member looks for behavioral expectations in the repository root
- **THEN** `CODE_OF_CONDUCT.md` exists and states them

### Requirement: Issue and PR templates exist
The repository SHALL include GitHub issue templates and a pull request
template under `.github/`.

#### Scenario: Contributor opens a new issue
- **WHEN** a contributor starts a new issue on GitHub
- **THEN** they are offered a structured template (e.g. bug report, feature request) under `.github/ISSUE_TEMPLATE/`

#### Scenario: Contributor opens a new pull request
- **WHEN** a contributor opens a new pull request on GitHub
- **THEN** `.github/PULL_REQUEST_TEMPLATE.md` prefills the description with the expected structure
