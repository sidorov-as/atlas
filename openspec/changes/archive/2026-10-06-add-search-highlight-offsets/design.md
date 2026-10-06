## Context

A search result's snippet is plain text plus `[start, end)` match ranges. Today the ranges are produced by the search plugin alone: it looks for words that start with a query word. The Meilisearch adapter gets the engine's own match markers in its formatted text, but strips them and returns only plain text, so what the engine matched is lost. A typo, word-form or synonym match therefore yields a good snippet window with nothing marked.

Separately, the plugin counts ranges in Python code points, the API passes them through unchanged, and the web client slices the text in UTF-16 code units. The two agree for text inside the Basic Multilingual Plane and drift by one position per astral character otherwise.

Constraints: the choice of engine must not change the plugin, sources or UI, so the plugin cannot gain engine-specific branches; the engine interface is a public plugin API, so changes must be additive; indexed text is untrusted and must never reach the client as markup.

## Goals / Non-Goals

**Goals:**
- Marked matches reflect what the engine matched, for any engine that can say so.
- Offset units are defined once for each boundary and are correct for all Unicode text.
- Existing and third-party engines keep working unchanged.

**Non-Goals:**
- Changing matching, ranking, snippet window size or title highlighting.
- Making the Postgres adapter supply highlights.
- Fuzzy matching inside the search plugin.

## Decisions

### 1. Engines return offsets next to the plain-text highlight

`SearchCandidate` gains an optional `highlight_matches`, a tuple of `(start, end)` code-point ranges relative to `highlight`. The plugin uses them when present and otherwise keeps its current prefix matching.

Alternatives considered:
- **Fuzzy matching in the plugin** (edit distance against snippet words). No contract change and engine-neutral, but it re-implements the engine's typo rules, drifts from them, and never covers stemming or synonyms.
- **Engine returns marked text** (markers in the highlight string). Needs no new field, but puts a markup convention into a field defined as plain text, and every consumer must parse and sanitize it, which is the injection surface the contract avoids.
- **Offsets (chosen).** Data rather than markup, optional, and additive. The plugin stays engine-neutral because the field describes any engine's matches the same way.

### 2. Code points inside the plugin and contract, UTF-16 at the API boundary

The contract and `Snippet` keep code points, which is what Python strings index by and what engines written in Python produce naturally. The API serializer converts to UTF-16 code units once, in a small helper, and the response schema states the unit.

Alternatives considered:
- **UTF-16 everywhere.** Correct for the only current client, but makes every Python engine author count surrogate pairs and leaks a JavaScript detail into the contract.
- **Client converts** (iterate by code points in the frontend). Keeps the API natural for Python, but every client has to know and repeat the conversion, and a missed one reproduces the bug.
- **Convert at the API (chosen).** One conversion in one place; the unit that crosses the wire is the unit the consumer slices in.

The helper walks the snippet text once, accumulating one extra unit for each code point above U+FFFF, and maps each start and end through the running total.

### 3. The Meilisearch adapter derives offsets in the same pass that cleans the text

The adapter replaces the engine's markers with sentinel characters, runs the existing tag stripping and whitespace collapsing, then scans the result once, recording each span between a start and an end sentinel and removing the sentinels. Offsets are computed on the final text, so they cannot disagree with it.

Alternatives considered:
- **Adjust offsets after cleaning** by tracking how each replacement shifts positions. Works, but is the fragile index bookkeeping this change is meant to avoid.
- **Plugin recomputes after its own cleaning.** Needs the markers to cross the contract, which decision 1 rejects.
- **Sentinels (chosen).** Sentinels are non-whitespace and are not touched by tag stripping or whitespace collapsing, so no arithmetic is needed.

The engine marks only the matched part of a word for a typo or a prefix (`paymen` of `payment`), so the adapter then grows each range to the edges of the words it touches and joins ranges that meet. Where a word ends follows what the engine itself does, checked against a running instance: it ends at anything that is not a letter or digit (`payment_gateway` and `billing-api` mark `payment` and `billing`), between a lowercase and an uppercase letter (`PaymentGateway`), and next to scripts written without spaces (CJK, kana and Thai are segmented by the engine, so widening would mark a whole phrase).

Alternatives considered for the partial marks:
- **Leave them partial.** Faithful to the engine, but a mark that covers `paymen` and not the `t` looks like a defect to a reader, and the result would differ from the whole-word marks the plugin gives for engines without offsets.
- **Widen by `\w`.** The rule the plugin's own matching uses, but `\w` includes `_`, so `[payment]_gateway` would mark the whole identifier, and it would mark whole runs of ideographs.
- **Widen by the engine's word rules (chosen).** A little more code, but the marks stay inside the words the engine found.

A marker inside an HTML tag is swallowed together with the tag, which leaves an unbalanced marker. The scan tolerates unbalanced and nested markers by dropping them rather than failing, so the worst outcome is a missing mark.

### 4. Validation at the contract, trust in the plugin

`SearchCandidate` validates offsets on construction (in range, ordered, non-overlapping, non-empty) the way it already validates the document id, so a faulty engine fails in its own tests. When offsets are present the plugin does not clean the highlight again, since that would invalidate them; the contract states that the highlight is final. This stays safe because the snippet is data and the client renders it as text.

Alternative considered: have the plugin clamp or drop bad offsets at query time. Rejected as the primary mechanism because it hides engine bugs, but cheap to keep as a last defense in the plugin so that one bad candidate cannot break a response.

## Risks / Trade-offs

- [Engine returns offsets for text that the plugin then changes] → The plugin leaves highlights with offsets untouched, and a contract test checks that offsets address the same text after the plugin's handling.
- [Marker inside markup produces a missing or partial mark] → Unbalanced markers are dropped; a missing mark is acceptable, a wrong one is not.
- [Word rules drift from the engine's] → The rules are small and covered by tests built from the engine's observed output; the conformance suite runs against a real instance.
- [Third-party clients assumed code points] → The documented unit is stated in the response schema and the changelog; the only known client is the bundled UI, which already slices in UTF-16.
- [Existing tests never exercised astral characters] → Add cases with emoji before and inside matches at every layer.

## Migration Plan

No data migration. The contract field is optional, so engines can adopt it independently. Ship the API conversion together with the UI test cases, since together they change what the client receives for non-BMP text. Rollback is a plain revert; nothing is stored.

## Open Questions

- Should highlight offsets also be used for titles if an engine later formats them? Not needed now.
