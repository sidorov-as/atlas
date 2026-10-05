import threading

import pytest
from atlas_plugin_api import (
    DuplicateSearchDocumentError,
    SearchDocument,
    get_catalog_entity_model,
    register_search_source,
)
from django.db import connection

from atlas_plugin_search import indexer
from atlas_plugin_search.models import IndexStatus, PendingChange


def _doc_id(note):
    return f"note:{note.pk}"


def test_drain_indexes_pending_documents_and_clears_them(active, engine, make_note):
    note = make_note("payment gateway", "settles card payments")

    result = indexer.drain_pending()

    assert result.upserted == 1
    assert _doc_id(note) in engine.documents
    assert PendingChange.objects.count() == 0
    assert IndexStatus.objects.get().last_drain_at is not None


def test_drain_deletes_documents_the_source_no_longer_produces(
    active, engine, make_note
):
    note = make_note("alpha")
    indexer.drain_pending()
    note.delete()

    result = indexer.drain_pending()

    assert result.deleted == 1
    assert engine.documents == {}
    assert PendingChange.objects.count() == 0


def test_drain_keeps_pending_rows_when_the_engine_is_down(active, engine, make_note):
    make_note("alpha")
    engine.fail = True

    result = indexer.drain_pending()

    assert result.failed == 1
    assert PendingChange.objects.count() == 1
    status = IndexStatus.objects.get()
    assert "engine is down" in status.last_error
    assert status.last_error_job == indexer.DRAIN
    assert status.last_error_at is not None
    assert status.last_drain_at is None


def test_next_drain_retries_and_clears_the_recorded_error(active, engine, make_note):
    note = make_note("alpha")
    engine.fail = True
    indexer.drain_pending()
    engine.fail = False

    indexer.drain_pending()

    assert _doc_id(note) in engine.documents
    assert PendingChange.objects.count() == 0
    status = IndexStatus.objects.get()
    assert status.last_error == ""
    assert status.last_error_job == ""
    assert status.last_drain_at is not None


def test_failing_source_is_recorded_and_its_rows_stay(active, source, make_note):
    make_note("alpha")
    source.failing_documents = True

    result = indexer.drain_pending()

    assert result.failed == 1
    assert PendingChange.objects.count() == 1
    assert "source is broken" in IndexStatus.objects.get().last_error


def test_a_change_landing_during_a_drain_stays_pending(active, engine, make_note):
    note = make_note("alpha")
    original_upsert = engine.upsert

    def upsert_then_edit(documents):
        original_upsert(documents)
        note.name = "beta"  # a write that lands while the batch is in flight
        note.save()

    engine.upsert = upsert_then_edit

    indexer.drain_pending()

    row = PendingChange.objects.get()
    assert row.document_id == _doc_id(note)
    assert row.generation == 2
    engine.upsert = original_upsert
    indexer.drain_pending()
    assert engine.documents[_doc_id(note)].title == "beta"
    assert PendingChange.objects.count() == 0


def test_drain_processes_more_rows_than_one_batch(active, engine, make_note):
    for i in range(7):
        make_note(f"note {i}")

    result = indexer.drain_pending(batch_size=3)

    assert result.upserted == 7
    assert len(engine.documents) == 7
    assert PendingChange.objects.count() == 0


def test_pending_ids_no_source_owns_are_dropped(active, engine):
    PendingChange.objects.create(document_id="ghost:1")
    PendingChange.objects.create(document_id="malformed")

    indexer.drain_pending()

    assert PendingChange.objects.count() == 0
    assert engine.documents == {}


def test_drain_and_rebuild_yield_while_another_session_holds_the_lock(
    active, make_note
):
    make_note("alpha")
    held, release = threading.Event(), threading.Event()

    def other_session():
        try:
            with indexer._indexing_lock() as acquired:
                assert acquired
                held.set()
                release.wait(10)
        finally:
            connection.close()

    thread = threading.Thread(target=other_session)
    thread.start()
    assert held.wait(10)
    try:
        assert indexer.drain_pending().skipped is True
        with pytest.raises(indexer.IndexingBusyError):
            indexer.rebuild_index()
    finally:
        release.set()
        thread.join()

    assert PendingChange.objects.count() == 1
    assert indexer.drain_pending().skipped is False


def test_rebuild_replaces_the_index_with_every_document(active, engine, make_note):
    keep = make_note("keep me")
    engine.documents["note:stale"] = SearchDocument(
        id="note:stale", kind="note", title="stale"
    )

    count = indexer.rebuild_index()

    assert count == 1
    assert set(engine.documents) == {_doc_id(keep)}
    assert IndexStatus.objects.get().last_rebuild_at is not None


def test_rebuild_repairs_changes_that_emitted_no_signal(active, engine, make_note):
    CatalogEntity = get_catalog_entity_model()

    note = make_note("before")
    indexer.drain_pending()
    CatalogEntity.objects.filter(pk=note.pk).update(name="after")  # no signal
    assert PendingChange.objects.count() == 0

    indexer.rebuild_index()

    assert engine.documents[_doc_id(note)].title == "after"


def test_rebuild_covers_and_clears_earlier_pending_changes(active, make_note):
    make_note("alpha")
    assert PendingChange.objects.count() == 1

    indexer.rebuild_index()

    assert PendingChange.objects.count() == 0


def test_failed_rebuild_keeps_pending_changes_and_records_the_error(
    active, engine, make_note
):
    make_note("alpha")
    engine.fail = True

    with pytest.raises(ConnectionError):
        indexer.rebuild_index()

    assert PendingChange.objects.count() == 1
    status = IndexStatus.objects.get()
    assert status.last_error_job == indexer.REBUILD
    assert status.last_rebuild_at is None


def test_duplicate_ids_across_sources_fail_the_rebuild(
    active, engine, source, make_note
):
    note = make_note("alpha")

    class Twin:
        id = "twin"
        kinds = ("twin",)
        watched_models = ()

        def document_ids_for_instance(self, instance):
            return []

        def documents(self, ids):
            return []

        def all_documents(self):
            # Same id as the notes source, which a distinct kind makes
            # impossible for SearchDocument itself: emulate a collision.
            yield SearchDocument(id=f"note:{note.pk}", kind="note", title="dup")

        def resolve(self, ids, actor):
            return []

    register_search_source(Twin(), owner="test.twin")

    with pytest.raises(DuplicateSearchDocumentError) as error:
        indexer.rebuild_index()

    assert error.value.document_id == f"note:{note.pk}"
    assert {error.value.first_source, error.value.second_source} == {"notes", "twin"}


def test_rebuild_if_index_empty_builds_when_sources_have_documents(
    active, engine, make_note
):
    make_note("alpha")

    assert indexer.rebuild_if_index_empty() is True
    assert len(engine.documents) == 1


def test_rebuild_if_index_empty_does_nothing_for_a_populated_index(
    active, engine, make_note
):
    make_note("alpha")
    indexer.rebuild_index()
    rebuilds = IndexStatus.objects.get().last_rebuild_at

    assert indexer.rebuild_if_index_empty() is False
    assert IndexStatus.objects.get().last_rebuild_at == rebuilds


def test_rebuild_if_index_empty_does_nothing_when_sources_are_empty(active, engine):
    assert indexer.rebuild_if_index_empty() is False
    assert engine.documents == {}


def test_rebuild_if_index_empty_does_nothing_when_the_engine_is_down(
    active, engine, make_note
):
    make_note("alpha")
    engine.fail = True

    assert indexer.rebuild_if_index_empty() is False
