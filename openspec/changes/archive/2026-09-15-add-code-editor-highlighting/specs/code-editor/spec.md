## ADDED Requirements

### Requirement: Shared syntax-highlighting code editor component
`core/frontend` SHALL export a reusable, theme-aware code editor component that renders syntax highlighting for `sql`, `yaml`, and `json` content, so any plugin can adopt structured-text editing without re-implementing Monaco wiring or theming. The component SHALL accept the content to edit, a change callback, and a language selection among `sql`, `yaml`, and `json`, and SHALL NOT contain logic specific to any single plugin's domain (e.g. API spec formats or SQL dialects).

#### Scenario: A plugin renders the editor with SQL highlighting
- **WHEN** a plugin renders the shared code editor with `language="sql"` and a SQL string as its content
- **THEN** the editor renders that content with SQL syntax highlighting

#### Scenario: A plugin renders the editor with YAML or JSON highlighting
- **WHEN** a plugin renders the shared code editor with `language="yaml"` or `language="json"` and a matching content string
- **THEN** the editor renders that content with the corresponding language's syntax highlighting

#### Scenario: Editing content invokes the caller's change callback
- **WHEN** a user types into the editor
- **THEN** the component invokes its change callback with the editor's current text, without persisting anything itself

### Requirement: Editor theme matches the active Gravity UI theme
The shared code editor SHALL render using a light or dark Monaco theme matching Atlas's current Gravity UI theme (light/dark), consistent with Atlas's brand colors, and SHALL update when the active theme changes.

#### Scenario: Editor matches a light Gravity UI theme
- **WHEN** the application is in its light Gravity UI theme and the shared code editor is rendered
- **THEN** the editor renders using the light Monaco theme matching Atlas's palette

#### Scenario: Editor matches a dark Gravity UI theme
- **WHEN** the application is in its dark Gravity UI theme and the shared code editor is rendered
- **THEN** the editor renders using the dark Monaco theme matching Atlas's palette

### Requirement: Editor loads lazily
The shared code editor component SHALL be loaded lazily (only when actually rendered), so that pages which do not render it do not pay its bundle cost.

#### Scenario: A page without the editor does not load it
- **WHEN** a user navigates to a page that does not render the shared code editor
- **THEN** the editor's underlying Monaco bundle is not loaded
