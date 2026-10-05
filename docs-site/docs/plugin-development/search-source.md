---
title: Write a search source
description: Make a plugin's data searchable by implementing and registering a SearchSource, including authorization in resolve.
audience:
  - plugin-author
page-type: tutorial
---

# Write a search source

A search source tells Atlas search what your plugin makes searchable, how a change
maps to documents, and who may see a hit. By the end you will have a registered
source and tests that prove deleted and unauthorized items never appear. Read
[Search architecture](../concepts/search-architecture.md) first for the model, and
the [Search index schema](../reference/search-index.md) for exact field rules.

Your plugin does not depend on the search plugin. It imports only
`atlas_plugin_api`, and registering is harmless when search is not selected.

## Starting state

You have a selected backend plugin with a Django model, here `Note`. Choose a
document kind that no other source uses, for example `note`. Document ids are
`note:<key>`, and the id alone must be enough to reload the row.

## Implement the source

A source is any object that satisfies the `SearchSource` protocol.

```python
from collections.abc import Iterable, Iterator, Sequence
from typing import Any

from atlas_plugin_api import SearchDocument, SearchHit, split_document_id

from .models import Note


def _pks(ids: Sequence[str]) -> list[int]:
    pks = []
    for document_id in ids:
        try:
            pks.append(int(split_document_id(document_id)[1]))
        except ValueError:
            continue
    return pks


class NoteSearchSource:
    id = "example.notes"
    kinds = ("note",)
    kind_labels = {"note": "Note"}  # optional display labels

    @property
    def watched_models(self) -> tuple[str, ...]:
        return (Note._meta.label,)

    def document_ids_for_instance(self, instance: Any) -> Iterable[str]:
        return [f"note:{instance.pk}"]  # also for deleted rows

    def documents(self, ids: Sequence[str]) -> Iterable[SearchDocument]:
        return [self._document(n) for n in Note.objects.filter(pk__in=_pks(ids))]

    def all_documents(self) -> Iterator[SearchDocument]:
        for note in Note.objects.iterator():
            yield self._document(note)

    def resolve(self, ids: Sequence[str], actor: Any) -> Sequence[SearchHit]:
        notes = Note.objects.filter(pk__in=_pks(ids)).visible_to(actor)
        return [
            SearchHit(
                id=f"note:{n.pk}",
                kind="note",
                title=n.title,
                link=f"/notes/{n.pk}",
                text=n.text,
            )
            for n in notes
        ]

    def _document(self, note: Note) -> SearchDocument:
        return SearchDocument(
            id=f"note:{note.pk}", kind="note", title=note.title, body=note.text
        )
```

What each method must do:

- **`watched_models`** lists `app_label.ModelName` labels. Their `post_save` and
  `post_delete` signals queue document ids. Include related models too.
- **`document_ids_for_instance`** returns the ids affected by a changed instance.
  For a related model return its owner's id. Return the id of a deleted object as
  well: `documents` will omit it and the indexer deletes it from the engine.
- **`documents(ids)`** returns live documents for the ids. Omit missing or
  ineligible ones; do not raise. Returning an id that was not requested is logged
  and ignored.
- **`all_documents()`** streams every document for a rebuild. Use `iterator()` or
  batching so a large table is not loaded at once.
- **`resolve(ids, actor)`** is the authorization point. Load live rows, apply your
  plugin's own read rules for `actor`, and return hits only for what the actor may
  read. Never trust the index. The `link` is an application-relative path and
  `text` is the plain text the snippet is built from.

Keep `body` plain text. A body above the configured bound (100 000 characters by
default) is truncated at a word boundary with a warning, so trim large content
yourself if only the start matters.

## Register it

Register from the plugin's `register_runtime()` hook, which runs after Django setup:

```python
def register_runtime() -> None:
    from atlas_plugin_api import register_search_source

    from .search_source import NoteSearchSource

    register_search_source(NoteSearchSource(), owner=PLUGIN.id)
```

Registration fails at startup if the source id or any of its kinds is already
registered by another plugin, and the error names both owners. The catalog's own
registration (`core/backend/server/apps/catalog/search_source.py`) is a complete
working reference.

Existing data is picked up by the next rebuild. Run
`python manage.py reindex` to see it immediately.

## Test authorization

Test the behaviours that matter, ideally against the real database:

1. **Indexing**: a saved `Note` appears in `documents([...])`; a deleted one does not.
2. **Mapping**: `document_ids_for_instance` returns the owner's id for a related
   model.
3. **Authorization**: `resolve` returns nothing for an actor who may not read the
   note, and nothing for a deleted id.
4. **Stale index**: delete the row without touching the index and confirm `resolve`
   still drops it.

## Verify

With search selected, create a note, run `python manage.py reindex`, then search
for a word from its title. Expect the note in results with your kind label and a
link that opens it. Edit the title and, with the scheduler running, expect the new
title to be searchable within about ten seconds. If it is not, follow [Diagnosing
a stale index](../concepts/search-indexing.md#diagnosing-a-stale-index).

Next: [Write a search engine](search-engine.md) or [Test a plugin](testing.md).
