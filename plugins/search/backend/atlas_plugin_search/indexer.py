"""Indexing: drain pending changes into the engine, rebuild the whole index.

Both operations run under one PostgreSQL advisory lock, so a drain never
interleaves with a rebuild (or with a second process running either). The
drain skips when the lock is taken; the rebuild reports it.
"""

import logging
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import reduce
from operator import or_

from atlas_plugin_api import (
    DuplicateSearchDocumentError,
    SearchDocument,
    SearchSource,
    get_search_source_lookup,
    split_document_id,
)
from django.db import connection
from django.db.models import Q

from . import runtime
from .models import IndexStatus, PendingChange

logger = logging.getLogger(__name__)

DRAIN_BATCH_SIZE = 500
_ADVISORY_LOCK_KEY = 0x41544C53  # "ATLS"
_ERROR_MAX_CHARS = 2000

DRAIN = "drain"
REBUILD = "rebuild"


class IndexingBusyError(RuntimeError):
    """Another drain or rebuild holds the indexing lock."""


@dataclass(frozen=True, slots=True)
class DrainResult:
    skipped: bool = False
    upserted: int = 0
    deleted: int = 0
    failed: int = 0
    """Pending rows left for the next run because their source or the engine
    failed."""


@contextmanager
def _indexing_lock() -> Iterator[bool]:
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(%s)", [_ADVISORY_LOCK_KEY])
        acquired = bool(cursor.fetchone()[0])
    try:
        yield acquired
    finally:
        if acquired:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_unlock(%s)", [_ADVISORY_LOCK_KEY])


def _status() -> IndexStatus:
    return IndexStatus.objects.get_or_create(pk=1)[0]


def _record_success(job: str) -> None:
    status = _status()
    now = datetime.now(UTC)
    if job == DRAIN:
        status.last_drain_at = now
    else:
        status.last_rebuild_at = now
    if status.last_error_job == job:
        status.last_error = ""
        status.last_error_at = None
        status.last_error_job = ""
    status.save()


def _record_failure(job: str, error: BaseException) -> None:
    status = _status()
    status.last_error = f"{type(error).__name__}: {error}"[:_ERROR_MAX_CHARS]
    status.last_error_at = datetime.now(UTC)
    status.last_error_job = job
    status.save()


def _remove_processed(rows: Sequence[PendingChange]) -> None:
    """Delete rows only while they still carry the generation that was read."""
    if rows:
        PendingChange.objects.filter(
            reduce(or_, (Q(pk=row.pk, generation=row.generation) for row in rows))
        ).delete()


def _group_by_source(
    document_ids: Sequence[str],
) -> tuple[dict[str, list[str]], list[str]]:
    lookup = get_search_source_lookup()
    grouped: dict[str, list[str]] = {}
    unowned: list[str] = []
    for document_id in document_ids:
        try:
            kind, _ = split_document_id(document_id)
        except ValueError:
            unowned.append(document_id)
            continue
        source = lookup.for_kind(kind)
        if source is None:
            unowned.append(document_id)
        else:
            grouped.setdefault(source.id, []).append(document_id)
    return grouped, unowned


def _documents_for(source: SearchSource, ids: list[str]) -> list[SearchDocument]:
    wanted = set(ids)
    documents = []
    for document in source.documents(ids):
        if document.id in wanted:
            documents.append(document)
        else:
            logger.warning(
                "Search source %s returned document %s that was not requested",
                source.id,
                document.id,
            )
    return documents


def drain_pending(batch_size: int = DRAIN_BATCH_SIZE) -> DrainResult:
    """Index pending changes: upsert present documents, delete absent ones.

    Pending rows are removed only after the engine accepted the change; a
    failing source or engine leaves its rows for the next run and is recorded
    in the status. Returns without doing anything when another indexing
    operation is running.
    """
    engine = runtime.get_engine()
    lookup = get_search_source_lookup()
    with _indexing_lock() as acquired:
        if not acquired:
            return DrainResult(skipped=True)
        upserted = deleted = failed = 0
        last_error: BaseException | None = None
        cursor_pk = 0
        while True:
            rows = list(
                PendingChange.objects.filter(pk__gt=cursor_pk).order_by("pk")[
                    :batch_size
                ]
            )
            if not rows:
                break
            cursor_pk = rows[-1].pk
            grouped, unowned = _group_by_source([row.document_id for row in rows])
            if unowned:
                # No registered source owns these ids (a source was removed,
                # or the id is malformed): nothing can ever index them, so
                # keep them out of the queue. The rebuild covers the rest.
                logger.warning("Dropping pending search changes for unowned ids")
                unowned_ids = set(unowned)
                _remove_processed([r for r in rows if r.document_id in unowned_ids])
            by_id = {row.document_id: row for row in rows}
            for source_id, ids in grouped.items():
                source = lookup.get(source_id)
                try:
                    documents = _documents_for(source, ids)
                    present = {document.id for document in documents}
                    missing = [i for i in ids if i not in present]
                    if documents:
                        engine.upsert(documents)
                    if missing:
                        engine.delete(missing)
                except Exception as exc:
                    logger.exception("Search drain failed for source %s", source_id)
                    last_error = exc
                    failed += len(ids)
                    continue
                upserted += len(documents)
                deleted += len(missing)
                _remove_processed([by_id[i] for i in ids])
        if last_error is not None:
            _record_failure(DRAIN, last_error)
        else:
            _record_success(DRAIN)
        return DrainResult(upserted=upserted, deleted=deleted, failed=failed)


def _all_documents() -> Iterator[SearchDocument]:
    """Every document of every source; ids must be unique across sources."""
    owners: dict[str, str] = {}
    for source in get_search_source_lookup().all():
        for document in source.all_documents():
            first = owners.setdefault(document.id, source.id)
            if first != source.id:
                raise DuplicateSearchDocumentError(
                    document.id, first_source=first, second_source=source.id
                )
            yield document


def rebuild_index() -> int:
    """Replace the engine's content with every document of every source.

    Returns the number of documents indexed. Pending changes queued before
    the rebuild started are covered by it and removed, unless they changed
    again meanwhile. Raises `IndexingBusyError` when another indexing
    operation is running.
    """
    engine = runtime.get_engine()
    with _indexing_lock() as acquired:
        if not acquired:
            raise IndexingBusyError("another search indexing run is in progress")
        covered = list(PendingChange.objects.all())
        count = 0

        def counted() -> Iterator[SearchDocument]:
            nonlocal count
            for document in _all_documents():
                count += 1
                yield document

        try:
            engine.replace_all(counted())
        except Exception as exc:
            logger.exception("Search rebuild failed")
            _record_failure(REBUILD, exc)
            raise
        _remove_processed(covered)
        _record_success(REBUILD)
        return count


def rebuild_if_index_empty() -> bool:
    """Run a rebuild when the engine holds nothing but the sources do.

    Covers first enablement, an engine switch and lost index data. Returns
    whether a rebuild ran.
    """
    engine = runtime.get_engine()
    health = engine.health()
    if not health.ok or health.document_count != 0:
        return False
    for source in get_search_source_lookup().all():
        if next(iter(source.all_documents()), None) is not None:
            break
    else:
        return False
    try:
        rebuild_index()
    except IndexingBusyError:
        return False
    return True
