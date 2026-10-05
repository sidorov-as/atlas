---
title: Search indexing algorithm
description: Step-by-step drain and rebuild algorithms, including de-duplication, batching, deletions, failure handling and what signals miss.
audience:
  - operator
  - plugin-author
page-type: concept
---

# Search indexing algorithm

Search results are only as fresh as the index. This page explains how changes
reach the index so you can reason about delays and diagnose a stale index. Field
and table details are in the [Search index schema](../reference/search-index.md);
how the pieces fit is in [Search architecture](search-architecture.md).

Indexing is an outbox plus a periodic reconcile: writes record what changed in
the same transaction, a frequent job applies those changes, and an infrequent job
rebuilds everything.

## Recording changes

The search plugin connects `post_save` and `post_delete` receivers once. For a
model a registered source watches:

1. The source maps the changed instance to the ids of the documents it affects
   (`document_ids_for_instance`). A deleted object's id is returned too.
2. The ids are de-duplicated and inserted into the pending table in a single
   statement inside the writer's transaction. A document already pending has its
   `generation` incremented instead of getting a second row.

Because the insert shares the transaction, a rolled-back write leaves no pending
row, and a committed write cannot lose one. A source that raises while mapping is
logged and skipped so it never fails the user's write; the rebuild covers it.

## Drain (every 10 seconds)

Run by the scheduler job `atlas.search.drain`.

1. Take the PostgreSQL advisory lock shared with the rebuild. If it is held, skip
   this run.
2. Read up to 500 pending rows in id order.
3. Group their ids by owning source. Ids that no source owns are removed from the
   queue with a warning, since nothing can ever index them.
4. For each source: call `documents(ids)`. Returned documents are upserted into the
   engine; requested ids that were not returned (deleted, removed, ineligible) are
   deleted from the engine.
5. Only after the engine accepted the change, delete the processed rows, and only
   those whose `generation` still matches what was read. A change that landed
   during the run keeps its row for the next one.
6. Repeat from the next batch until no rows remain.
7. Record the outcome: success clears a previous drain error and sets
   `lastDrainAt`; any failure stores the message and time.

If a source or the engine fails, that source's rows stay pending and are retried on
the next run. Other sources in the same batch still complete.

## Rebuild (every 6 hours)

Run by `atlas.search.rebuild`, by the `reindex` command, and once at scheduler start
if the index is empty.

1. Take the advisory lock. A rebuild that finds it held reports that another
   indexing run is in progress.
2. Remember the current pending rows.
3. Stream `all_documents()` from every source to the engine's `replace_all`, which
   swaps the index atomically. If it fails partway the previous index stays
   queryable.
4. Remove the remembered pending rows, again only when their `generation` is
   unchanged.
5. Record success, or the failure.

A document id produced by two sources aborts the rebuild before the swap.

### First run

When the scheduler starts it runs `atlas.search.initial_rebuild` once. It rebuilds
only if the engine is healthy and reports zero documents while at least one source
has documents. This covers first enablement, switching engines, and lost index
data without waiting for the rebuild interval.

## What signals miss

Signals fire for `save()` and `delete()` on model instances. They do not fire for
queryset `update()`, `bulk_update()`, bulk deletes or raw SQL, and nothing is
recorded while the search plugin is inactive. The rebuild repairs all of these,
so freshness for such changes equals the rebuild interval.

## Diagnosing a stale index

Read `GET /api/plugins/atlas.search/status/` and decide which part is at fault:

| Observation | Likely cause | Next step |
| --- | --- | --- |
| `pendingCount` grows and `oldestPendingAgeSeconds` keeps rising, `lastDrainAt` is old | The scheduler is not running, or the drain skips because a long rebuild holds the lock | Check the scheduler process; see [Run without a scheduler](../operating-atlas/search.md#run-without-a-scheduler) |
| `engineHealthy` is false | The engine is unreachable | Fix the engine; pending rows wait and are retried |
| `hasError` is true, `lastErrorJob` is `drain` | A source or the engine keeps failing | Read `lastError` (administrators) and the backend log for the source id |
| Backlog is zero, one entity is still missing | A bulk operation bypassed signals | Wait for the rebuild, or run `reindex` |
| `documentCount` is much lower than the catalog | Index not built or engine switched | Run `reindex` |

Results can also be *missing* rather than stale when `resolve` filters them: a
removed entity or one the caller may not read never appears, regardless of the
index.
