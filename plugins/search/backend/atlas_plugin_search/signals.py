"""Record pending changes for the models registered sources watch.

Receivers are connected once without a sender and look the watching sources
up on every call: `register_runtime()` hooks run in manifest order, so the
sources may not be registered yet when the receivers are connected.
"""

import logging
from collections.abc import Sequence

from atlas_plugin_api import SearchSource, get_search_source_lookup
from django.db import DatabaseError, connection, transaction
from django.db.models.signals import post_delete, post_save

from . import runtime
from .models import PendingChange

logger = logging.getLogger(__name__)

_DISPATCH_UID = "atlas_plugin_search"

_watchers_cache: tuple[
    tuple[SearchSource, ...], dict[str, tuple[SearchSource, ...]]
] = (
    (),
    {},
)


def _watchers() -> dict[str, tuple[SearchSource, ...]]:
    global _watchers_cache
    sources = get_search_source_lookup().all()
    if _watchers_cache[0] != sources:
        by_model: dict[str, list[SearchSource]] = {}
        for source in sources:
            for model_label in source.watched_models:
                by_model.setdefault(model_label, []).append(source)
        _watchers_cache = (sources, {k: tuple(v) for k, v in by_model.items()})
    return _watchers_cache[1]


def record_pending(document_ids: Sequence[str]) -> None:
    """Mark `document_ids` pending in the current transaction, de-duplicated.

    A document already pending gets its `generation` bumped, which tells a
    running indexer that what it read is no longer current.
    """
    unique = sorted(set(document_ids))
    if not unique:
        return
    table = connection.ops.quote_name(PendingChange._meta.db_table)
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute(
            f"INSERT INTO {table} (document_id, generation, queued_at) "
            "SELECT unnest(%s::text[]), 1, now() "
            "ON CONFLICT (document_id) DO UPDATE "
            f"SET generation = {table}.generation + 1",
            [unique],
        )


def _on_model_change(sender, instance, raw=False, **kwargs) -> None:
    if raw or not runtime.is_active():
        return
    sources = _watchers().get(sender._meta.label)
    if not sources:
        return
    document_ids: set[str] = set()
    for source in sources:
        try:
            document_ids.update(source.document_ids_for_instance(instance))
        except Exception:
            # A faulty source must not fail the write that triggered it; the
            # periodic rebuild repairs whatever is missed.
            logger.exception(
                "Search source %s failed to map a %s change to documents",
                source.id,
                sender._meta.label,
            )
    try:
        record_pending(list(document_ids))
    except DatabaseError:
        logger.exception("Could not record pending search changes")


def connect() -> None:
    post_save.connect(_on_model_change, dispatch_uid=f"{_DISPATCH_UID}.save")
    post_delete.connect(_on_model_change, dispatch_uid=f"{_DISPATCH_UID}.delete")


def disconnect() -> None:
    post_save.disconnect(dispatch_uid=f"{_DISPATCH_UID}.save")
    post_delete.disconnect(dispatch_uid=f"{_DISPATCH_UID}.delete")
