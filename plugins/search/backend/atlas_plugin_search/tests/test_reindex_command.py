import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from atlas_plugin_search import indexer
from atlas_plugin_search.models import IndexStatus, PendingChange


def test_reindex_builds_the_whole_index_without_a_scheduler(
    active, engine, make_note, capsys
):
    make_note("alpha")
    make_note("beta")

    call_command("reindex")

    assert len(engine.documents) == 2
    assert PendingChange.objects.count() == 0
    assert IndexStatus.objects.get().last_rebuild_at is not None
    assert "Indexed 2 documents" in capsys.readouterr().out


def test_reindex_fails_clearly_when_search_is_not_active(db):
    with pytest.raises(CommandError, match="not active"):
        call_command("reindex")


def test_reindex_reports_an_engine_failure(active, engine, make_note):
    make_note("alpha")
    engine.fail = True

    with pytest.raises(CommandError, match="Rebuild failed"):
        call_command("reindex")


def test_reindex_reports_a_busy_index(active, monkeypatch):
    def busy():
        raise indexer.IndexingBusyError("another search indexing run is in progress")

    monkeypatch.setattr(indexer, "rebuild_index", busy)

    with pytest.raises(CommandError, match="in progress"):
        call_command("reindex")
