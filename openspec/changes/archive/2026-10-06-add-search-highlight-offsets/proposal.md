## Why

Search snippets mark query matches with `[start, end)` offsets, and two things make those marks wrong today.

1. The search plugin finds matches itself by looking for words that start with a query word. Meilisearch also matches typos, word forms and synonyms, so a query like `paymnt` returns the document containing `payment` but its snippet has no marked match. The engine knows what it matched, and that knowledge is thrown away when its highlight is reduced to plain text.
2. Offsets are counted in Python code points, while the web client slices text in UTF-16 code units. Any character outside the Basic Multilingual Plane (emoji, rare CJK, mathematical alphabets) before a match shifts the highlight by one position per such character, so a snippet for `😀 payment` highlights ` paymen`.

Both problems concern the same thing, the meaning of snippet match offsets, so they are fixed together and the offset units are defined once.

## What Changes

- An engine can optionally return match offsets with its highlight. They are relative to the returned highlight text and counted in code points. An engine that does not supply them behaves as before.
- The search plugin uses engine-supplied offsets when present and falls back to its own word-prefix matching otherwise.
- The Meilisearch adapter computes offsets from the engine's formatted text instead of discarding the match markers, producing plain text and offsets that agree with each other even when markup is stripped and whitespace is collapsed.
- The search API returns snippet match offsets in UTF-16 code units, converting from the plugin's internal code points at the API boundary. The unit is stated in the response schema.
- Invalid engine offsets (out of range, unordered, overlapping) are rejected or dropped rather than rendered.
- Tests cover typo, stem and synonym matches, markup in indexed text, and text containing characters outside the BMP.

Out of scope: changing which documents match or how they rank, snippet window size, highlighting of titles, and any engine-specific code in the search plugin. The Postgres adapter does not supply highlights and is unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `search-contract`: a candidate may carry match offsets alongside its plain-text highlight, with defined units and validity rules.
- `search-api`: snippets use engine-supplied match offsets when available, and returned offsets are in UTF-16 code units.
- `search-meilisearch-engine`: the adapter returns offsets for everything the engine matched, including typos and word forms, consistent with the plain-text highlight it returns.
- `search-ui`: marks are drawn at the returned offsets, which line up with the rendered text for any character.

## Impact

- `plugin-api` (`atlas_plugin_api/search.py`): `SearchCandidate` gains an optional field. The change is additive, so existing and third-party engines keep working.
- `plugins/search` backend: snippet building and the API serializer and schema for snippets.
- `plugins/search-meilisearch` backend: highlight extraction in the engine adapter.
- `plugins/search` frontend: no behavior change expected beyond correct marks; its tests gain cases with non-BMP text.
- No migrations, no new dependencies, no change to the response shape apart from the documented offset unit.
