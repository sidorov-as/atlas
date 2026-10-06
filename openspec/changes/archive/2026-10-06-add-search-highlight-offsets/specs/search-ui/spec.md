## ADDED Requirements

### Requirement: Snippet marks follow the returned offsets
The dialog SHALL mark in each snippet exactly the ranges the response gives, taken in UTF-16 code units of the snippet text, and SHALL render the marked and unmarked parts as text.

#### Scenario: Snippet with emoji before a match
- **WHEN** a snippet's text has an emoji before a matched word
- **THEN** the mark covers exactly that word

#### Scenario: Match at an engine-supplied offset
- **WHEN** a snippet's match is for a typo of the query
- **THEN** the mark covers the matched word
