## MODIFIED Requirements

### Requirement: Native highlights and typo tolerance are declared
The adapter SHALL declare that it supplies highlights and typo tolerance, SHALL return highlights in a form the search plugin can render without injecting markup, and SHALL return the offsets of everything the engine matched in the returned highlight, including typos and word forms of the query. Each offset range SHALL cover the whole word it touches, where a word ends at anything that is not a letter or digit, between a lowercase and an uppercase letter, and next to a script written without spaces.

#### Scenario: Misspelled query
- **WHEN** a query contains a small typo of an indexed word
- **THEN** the intended document is still returned

#### Scenario: Misspelled query highlight
- **WHEN** a query contains a small typo of a word in the returned highlight
- **THEN** the candidate's match offsets cover that word

#### Scenario: Partly matched word
- **WHEN** the engine marks only the matched part of a word, as it does for a typo or a prefix of the query
- **THEN** the candidate's match offsets cover that whole word

#### Scenario: Word boundaries the engine uses
- **WHEN** a match touches a word joined by an underscore, hyphen or camelCase boundary to other words, or a word in a script written without spaces
- **THEN** the offsets stop at that boundary instead of covering the neighbouring word or phrase

#### Scenario: Highlight with markup in content
- **WHEN** indexed text contains HTML
- **THEN** the returned highlight carries no executable markup

#### Scenario: Offsets agree with stripped text
- **WHEN** the highlight contains HTML tags or runs of whitespace that are removed or collapsed before it is returned
- **THEN** the match offsets address the same words in the returned text as in the engine's formatted text
