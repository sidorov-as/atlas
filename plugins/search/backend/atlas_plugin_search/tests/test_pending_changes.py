import pytest
from atlas_plugin_api import get_catalog_entity_model
from django.db import transaction

from atlas_plugin_search import signals
from atlas_plugin_search.models import PendingChange


def _ids():
    return set(PendingChange.objects.values_list("document_id", flat=True))


def test_saving_a_watched_instance_records_its_document(active, make_note):
    note = make_note("alpha")

    assert _ids() == {f"note:{note.pk}"}


def test_rolled_back_write_leaves_no_pending_change(active, make_note):
    with pytest.raises(RuntimeError), transaction.atomic():
        make_note("alpha")
        raise RuntimeError("roll back")

    assert PendingChange.objects.count() == 0


def test_repeated_writes_coalesce_into_one_entry(active, make_note):
    note = make_note("alpha")
    first = PendingChange.objects.get()

    note.name = "beta"
    note.save()
    note.name = "gamma"
    note.save()

    row = PendingChange.objects.get()
    assert row.pk == first.pk
    assert row.generation == 3
    assert row.queued_at == first.queued_at


def test_delete_is_recorded(active, make_note):
    note = make_note("alpha")
    PendingChange.objects.all().delete()
    document_id = f"note:{note.pk}"

    note.delete()

    assert _ids() == {document_id}


def test_unwatched_models_record_nothing(active, user):
    assert PendingChange.objects.count() == 0


def test_nothing_is_recorded_when_the_plugin_is_not_active(source, make_note):
    from atlas_plugin_api import register_search_source

    register_search_source(source, owner="test.source")
    signals.connect()  # receivers exist, but no engine was selected

    make_note("alpha")

    assert PendingChange.objects.count() == 0


def test_nothing_is_recorded_before_register_runtime(source, make_note):
    from atlas_plugin_api import register_search_source

    register_search_source(source, owner="test.source")

    make_note("alpha")

    assert PendingChange.objects.count() == 0


def test_a_failing_source_mapping_does_not_fail_the_write(active, source, make_note):
    def boom(instance):
        raise RuntimeError("mapping broke")

    source.document_ids_for_instance = boom

    note = make_note("alpha")

    assert note.pk is not None
    assert PendingChange.objects.count() == 0


def test_fixture_loading_is_ignored(active, source):
    CatalogEntity = get_catalog_entity_model()

    from atlas_plugin_search.signals import _on_model_change

    _on_model_change(CatalogEntity, CatalogEntity(name="x"), raw=True)

    assert PendingChange.objects.count() == 0
