# search-ui Specification

## Purpose
The shell contribution for search and the search box and dialog experience.

## Requirements

### Requirement: A single-occupant shell contribution for search
The frontend plugin contract SHALL provide a contribution type for global search that at most one plugin may supply. Composition SHALL fail identifying both plugins when two supply it. The application shell SHALL render the contribution when present and SHALL render nothing in its place when absent.

#### Scenario: No search plugin installed
- **WHEN** no installed plugin supplies the contribution
- **THEN** the shell shows no search control and no error

#### Scenario: Two plugins supply search
- **WHEN** two plugins supply the contribution
- **THEN** composition fails before the router is built

### Requirement: Search box opens a results dialog
The search plugin's UI SHALL present a search box in the shell that opens a dialog when focused or activated, and SHALL open the same dialog from a keyboard shortcut. The dialog SHALL show results as the user types after a short delay, grouped or labelled by kind, with title, snippet and a kind label.

#### Scenario: Open and type
- **WHEN** the user activates the search box and types a query
- **THEN** the dialog shows matching results after a short delay without a page reload

#### Scenario: Keyboard shortcut
- **WHEN** the user presses the documented shortcut
- **THEN** the dialog opens with the input focused

#### Scenario: No results
- **WHEN** no result matches
- **THEN** the dialog shows an empty-state message

### Requirement: Keyboard navigation and activation
The dialog SHALL support moving through results with arrow keys, opening the highlighted result with Enter, and closing with Escape. Opening a result SHALL navigate to its link target and close the dialog.

#### Scenario: Open with keyboard
- **WHEN** the user moves to a result with arrow keys and presses Enter
- **THEN** the application navigates to that result and the dialog closes

### Requirement: The UI depends only on the HTTP contract
The search UI SHALL use only the search and status endpoints and SHALL NOT import other plugins or know which engine is in use.

#### Scenario: Engine swapped
- **WHEN** the engine plugin is replaced
- **THEN** the UI works without change

### Requirement: Degraded states are visible
The dialog SHALL show a distinct message when the search service is unavailable and MAY show a notice when the index is stale according to status.

#### Scenario: Service unavailable
- **WHEN** the search endpoint reports the service unavailable
- **THEN** the dialog shows an unavailable message rather than "no results"

### Requirement: Snippet marks follow the returned offsets
The dialog SHALL mark in each snippet exactly the ranges the response gives, taken in UTF-16 code units of the snippet text, and SHALL render the marked and unmarked parts as text.

#### Scenario: Snippet with emoji before a match
- **WHEN** a snippet's text has an emoji before a matched word
- **THEN** the mark covers exactly that word

#### Scenario: Match at an engine-supplied offset
- **WHEN** a snippet's match is for a typo of the query
- **THEN** the mark covers the matched word

### Requirement: Query input is rendered safely
Result titles and snippets SHALL be rendered as text so that indexed content cannot inject markup.

#### Scenario: Title contains markup
- **WHEN** a result title contains HTML
- **THEN** it is displayed as literal text
