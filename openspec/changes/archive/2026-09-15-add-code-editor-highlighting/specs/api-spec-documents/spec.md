## ADDED Requirements

### Requirement: Inline spec editor shows format-appropriate syntax highlighting
When a user edits an API's `spec_content` with `spec_source` set to `inline`, the editor SHALL detect whether the current content is JSON or YAML from the content itself (no stored format field exists) and render it with the corresponding syntax highlighting, defaulting to YAML highlighting when the content does not look like JSON.

#### Scenario: JSON-looking content is highlighted as JSON
- **WHEN** a user's inline spec content, trimmed, begins with `{` or `[`
- **THEN** the editor renders it with JSON syntax highlighting

#### Scenario: Non-JSON-looking content is highlighted as YAML
- **WHEN** a user's inline spec content, trimmed, does not begin with `{` or `[`
- **THEN** the editor renders it with YAML syntax highlighting

### Requirement: Inline spec editor surfaces invalid JSON/YAML before save
The inline spec editor SHALL attempt to parse the current content as YAML-or-JSON on change and SHALL show a visible inline error when parsing fails, before the user saves.

#### Scenario: Invalid content shows an inline error
- **WHEN** a user's inline spec content does not parse as valid JSON or YAML
- **THEN** the editor shows a visible inline error indicating the content is invalid

#### Scenario: Valid content shows no error
- **WHEN** a user's inline spec content parses successfully as JSON or YAML
- **THEN** the editor shows no parse error
