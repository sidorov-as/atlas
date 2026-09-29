## MODIFIED Requirements

### Requirement: Full Markdown documentation is rendered in the detail experience
The Overview tab for System, Component, Resource, and API SHALL render `metadata.documentation` as formatted Markdown. A Flow detail page SHALL render its `documentation` as formatted Markdown below the graph and Steps section. Empty documentation SHALL use an explicit empty state rather than rendering the short summary a second time. Rendering SHALL use a Markdown/SVG toolchain with no known high-severity denial-of-service or sanitization-bypass vulnerability in its resolved dependency versions, and SHALL reject or neutralize adversarial input (pathological link/URL patterns, SVG-embedded executable content, deeply-nested or aliased YAML front matter) without executing it or exhausting server/client resources.

#### Scenario: API Overview renders full documentation
- **WHEN** a user opens an API whose `metadata.documentation` contains Markdown formatting
- **THEN** Overview renders the formatted documentation and does not use `metadata.description` as its body content

#### Scenario: Flow documentation follows graph and steps
- **WHEN** a user opens a Flow with steps and documentation
- **THEN** the graph and Steps appear before the formatted documentation section

#### Scenario: Adversarial Markdown does not degrade rendering performance
- **WHEN** `metadata.documentation` contains a link/URL pattern crafted to trigger quadratic-complexity scanning in the Markdown link detector
- **THEN** rendering completes without exhibiting pathological (quadratic-time) scan behavior

#### Scenario: SVG-embedded scripts are not rendered as executable
- **WHEN** `metadata.documentation` contains an SVG with an embedded `<script>`, an executable link disguised via namespace or control-character obfuscation, or executable HTML inside a `foreignObject` element
- **THEN** the rendered output does not execute or expose that content as active script
