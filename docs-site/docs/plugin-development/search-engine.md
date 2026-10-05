---
title: Write a search engine
description: Implement and register a SearchEngine adapter plugin, declare its capabilities, and verify it with the conformance suite.
audience:
  - plugin-author
page-type: tutorial
---

# Write a search engine

An engine adapter stores the search index and ranks matches. It is a separate
plugin, so a fork or an out-of-tree plugin can swap storage without touching the
search plugin or any source. By the end you will have an adapter that passes the
shared conformance suite. Background is in [Search
architecture](../concepts/search-architecture.md). Two adapters are complete
references: `atlas.search-postgres` (`plugins/search-postgres/`) keeps the index in the
application's database, and `atlas.search-meilisearch` (`plugins/search-meilisearch/`)
talks to a separate server over HTTP. [Choose a reference](#reference-adapters) below.

The adapter is an ordinary plugin: it needs a descriptor with its Django apps (and
migrations if it stores data in the database) and it must be selected in the
distribution manifest to take part. See [Choose a plugin layout](plugin-layouts.md).

## Implement the engine

An engine satisfies the `SearchEngine` protocol:

```python
from atlas_plugin_api import (
    EngineCapabilities,
    EngineHealth,
    SearchCandidate,
    SearchDocument,
)


class MyEngine:
    id = "my-engine"
    capabilities = EngineCapabilities(highlights=False, typo_tolerance=False)

    def upsert(self, documents): ...
    def delete(self, ids): ...
    def replace_all(self, documents): ...
    def query(self, text, *, kinds=None, limit=20, offset=0): ...
    def health(self) -> EngineHealth: ...
```

| Method | Contract |
| --- | --- |
| `upsert(documents)` | Insert or replace by `document.id`. The same id twice in one call: the last wins. |
| `delete(ids)` | Remove documents. Unknown ids are ignored, not errors. |
| `replace_all(documents)` | Replace the whole index from a stream, atomically. If it fails partway the previous content must stay queryable. Do not hold the whole stream in memory. |
| `query(text, kinds, limit, offset)` | Return `SearchCandidate(id, score)` ordered by descending relevance. Treat `text` as data, not query syntax. Return no match as an empty list. `kinds=None` means all kinds. |
| `health()` | Return `EngineHealth(ok=...)`. Set `document_count` if you can: when it is `0`, the first-run rebuild can fill an empty index. |

Rank so that a match in `title` outweighs one in `body`. Engines are not required to
rank identically, but a title match winning is part of the conformance suite.

### Capability flags

`EngineCapabilities.highlights=True` tells the search plugin that candidates carry a
plain-text `highlight` to use as the snippet. Leave it `False` and core builds the
snippet from the resolved text, which gives the same behaviour on every engine.
A highlight must be plain text with no markup.

`typo_tolerance=True` declares that a small misspelling of an indexed word still
finds the document. It is informational for operators and tests; leave it `False` if
your engine matches exact terms.

Never pass engine markup through. The Meilisearch adapter asks the engine for private
marker characters around matches, strips them and any HTML tags from the formatted
text, and returns plain text, so indexed content such as `<script>` cannot reach the
UI as markup.

## Reference adapters

| | `atlas.search-postgres` | `atlas.search-meilisearch` |
| --- | --- | --- |
| Storage | Table in the application database | Separate Meilisearch server |
| Extra service | None | Declared as a [required service](required-services.md) |
| Writes | Synchronous, in a transaction | Asynchronous; waits for the engine's task to finish |
| `replace_all` | Delete and refill in one transaction | Build a temporary index, swap it in, delete the old one |
| Ranking | `title` over `body` through weights | Ordered `searchableAttributes`: title, summary, body |
| Capabilities | `highlights=False` | `highlights=True`, `typo_tolerance=True` |

Read the Meilisearch adapter when your engine is remote. It shows these patterns:

- **Restricted ids.** The engine only accepts a narrow identifier character set, but
  search ids look like `kind:key`. `ids.py` encodes each id reversibly and the original
  is stored in a field and returned from queries. Do not change document ids in the
  contract to suit one engine.
- **Acknowledge only what is applied.** `upsert` and `delete` wait until the engine
  reports the task finished and raise on failure or timeout, so the drain job keeps
  its pending rows and retries. Returning early would lose updates.
- **Atomic replace without transactions.** `replace_all` streams into a fresh index,
  applies the settings, swaps and removes the old one. On failure it deletes the
  temporary index and the live one is untouched.
- **Operator-supplied endpoint.** The address and key come from the plugin's own
  [configuration](plugin-configuration.md), and the client talks to that target only.
  An engine that needs a server should declare it so operators do not wire it by hand;
  see [Declare a required service](required-services.md).

## Register it

```python
def register_runtime() -> None:
    from atlas_plugin_api import register_search_engine

    register_search_engine(MyEngine(), owner=PLUGIN.id)
```

Use `PLUGIN.id` as `owner`. Operators select your engine by that plugin id, through
the search plugin's `engine` setting. A disabled plugin does not run
`register_runtime()` and so registers nothing.

## Run the conformance suite

Subclass `SearchEngineConformance` in your own tests and implement `make_engine`:

```python
import pytest
from atlas_plugin_api.search_conformance import SearchEngineConformance


class TestMyEngineConformance(SearchEngineConformance):
    @pytest.fixture(autouse=True)
    def _database(self, db):
        """Only needed when the adapter stores its index in the database."""

    def make_engine(self):
        return MyEngine()
```

An adapter for a remote engine runs the same suite against a real instance. The
Meilisearch tests (`tests/test_conformance.py`) read the instance from
`ATLAS_TEST_MEILISEARCH_URL` (and `ATLAS_TEST_MEILISEARCH_KEY`), are skipped without
it, and fail instead when `ATLAS_REQUIRE_MEILISEARCH=1`; CI and `make ci` start one. A
fast unit suite covers failures and timeouts that a healthy instance never shows. Give
each test its own index so the empty-index requirement holds.

`make_engine` must return an engine whose index is empty and isolated from other
tests. The suite checks identity and capabilities, health, upsert and replacement,
delete (including unknown ids), empty and unmatched queries, descending scores,
title-over-body ranking, kind filtering, limit and offset paging, queries with
special characters, `replace_all` (including with no documents and a failure
partway) and that highlights appear only when declared. Run it with `pytest` from
the backend environment; every check must pass.

## Verify

1. Select the adapter in a development manifest and resolve the lock ([Distribution
   manifest and lock](../reference/distribution-manifest.md)).
2. Start the backend. With exactly one engine selected it is used automatically; with
   several, set `engine` to your plugin id or startup fails and lists them.
3. Run `python manage.py reindex`, then query the search endpoint and check
   `GET /api/plugins/atlas.search/status/` reports your engine healthy (`engine` is
   visible to administrators).

Next: [Write a search source](search-source.md).
