## MODIFIED Requirements

### Requirement: Snippets are consistent across engines
The system SHALL provide a snippet for a result from the resolved hit's text around the first query match, unless the engine declares it supplies highlights, in which case the engine's highlights SHALL be used. When the engine supplies match offsets with a highlight, the snippet's marked matches SHALL be those offsets; otherwise the system SHALL locate the matches itself. Snippet text SHALL be returned in a form that cannot inject markup.

#### Scenario: Core-generated snippet
- **WHEN** the engine does not supply highlights and the body contains the query
- **THEN** the result includes a snippet around the match with the match marked

#### Scenario: Engine-supplied offsets
- **WHEN** the engine supplies a highlight with match offsets, including for a typo, word form or synonym of the query
- **THEN** the snippet marks exactly those offsets

#### Scenario: Engine highlight without offsets
- **WHEN** the engine supplies a highlight without match offsets
- **THEN** the system locates the query matches in the highlight itself

#### Scenario: Match only in title
- **WHEN** the match is in the title and not in the body
- **THEN** the result's snippet falls back to the summary or beginning of the body

#### Scenario: Markup in indexed text
- **WHEN** the body contains HTML or markdown markup
- **THEN** the snippet carries no executable markup

## ADDED Requirements

### Requirement: Snippet match offsets are UTF-16 code units
The response SHALL give snippet match offsets as `[start, end)` ranges counted in UTF-16 code units of the snippet text, and the response schema SHALL state this unit. The system SHALL convert from any other internal unit before responding.

#### Scenario: Match after a character outside the BMP
- **WHEN** a snippet's text contains an emoji before a matched word
- **THEN** the returned offsets address the matched word when used to slice the text in UTF-16 code units

#### Scenario: Text within the BMP
- **WHEN** a snippet's text contains only characters within the Basic Multilingual Plane
- **THEN** the returned offsets are the same as the character positions of the matches
