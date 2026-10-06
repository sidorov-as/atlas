## 1. Contract

- [x] 1.1 Add optional `highlight_matches` (tuple of `(start, end)` code-point ranges) to `SearchCandidate` in `plugin-api` and document its units and the "highlight is final" rule
- [x] 1.2 Validate offsets on construction: in range of `highlight`, ordered, non-overlapping, non-empty, and only valid with a highlight
- [x] 1.3 Add contract tests for valid offsets, no offsets, and each invalid case
- [x] 1.4 Update the test fake engine to optionally return offsets

## 2. Search plugin snippets

- [x] 2.1 In `highlight_snippet`, use the candidate's offsets without cleaning the highlight again when they are present; keep prefix matching when they are absent
- [x] 2.2 Pass the candidate's offsets from `service.py` to `highlight_snippet`
- [x] 2.3 Drop offsets that fall outside the highlight text as a last defense, so one bad candidate cannot break a response
- [x] 2.4 Add snippet tests: engine offsets for a typo match, offsets absent, and offsets present with text that cleaning would otherwise change

## 3. API offset units

- [x] 3.1 Add a helper that converts code-point ranges to UTF-16 code-unit ranges for a given text
- [x] 3.2 Apply it when building `SnippetOut` in `api/views.py`
- [x] 3.3 State the UTF-16 unit in `SnippetOut` in `api/schemas.py`
- [x] 3.4 Add tests for the helper (ASCII, Cyrillic, emoji before and inside a match, match at the ends) and an API test with an emoji snippet

## 4. Meilisearch adapter

- [x] 4.1 Replace the stripping of match markers in `to_plain_highlight` with sentinels, run the existing tag and whitespace cleaning, then scan once to collect offsets and remove the sentinels
- [x] 4.2 Tolerate unbalanced and nested markers by dropping them
- [x] 4.3 Return the offsets in `SearchCandidate` from `_candidate`
- [x] 4.4 Add engine tests: plain match, typo match, markup and whitespace collapsed before a match, marker inside a tag, and text with characters outside the BMP
- [x] 4.5 Grow each range to the edges of the words it touches, using the engine's word boundaries (non letters and digits, camelCase, scripts written without spaces), and join ranges that meet
- [x] 4.6 Add engine tests: typo and prefix widened to the whole word, Cyrillic, `_` / `-` / camelCase boundaries, CJK, kana and Thai left alone, ranges joined, offsets beyond the BMP
- [x] 4.7 Check the marking on a running Meilisearch instance for typo, prefix, separator, camelCase, CJK and Cyrillic queries and make the rules match

## 5. Frontend

- [x] 5.1 Add `HighlightedText` and `SearchDialog` test cases with an emoji before a match and with a typo match, confirming the mark covers the intended word
- [x] 5.2 Confirm the existing guards in `HighlightedText` still behave with the corrected offsets

## 6. Documentation and verification

- [x] 6.1 Document `highlight_matches` in the search engine guide and the UTF-16 unit of snippet `matches` in the search reference
- [x] 6.2 Run the search plugin, Meilisearch adapter, plugin-api and frontend test suites
- [x] 6.3 With a running Meilisearch instance, search with a typo (`paymnt` for `payment`) and check the marked word in the dialog
- [x] 6.4 Run `openspec validate add-search-highlight-offsets --strict`
