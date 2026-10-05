"""A disabled search plugin does nothing; core skips every one of its hooks."""

from atlas_plugin_api import register_search_engine, register_search_source
from django.db.models.signals import post_save
from server.apps.plugins.resolver import load_selected_descriptors
from server.apps.plugins.runtime import load_runtime_entry_points

from atlas_plugin_search import runtime
from atlas_plugin_search.models import PendingChange

_SELECTED = ("atlas_plugin_search.plugin",)


def test_disabled_plugin_registers_nothing_and_stays_inactive(
    db, engine, source, make_note
):
    register_search_source(source, owner="test.source")
    register_search_engine(engine, owner="test.engine")
    descriptors = load_selected_descriptors(_SELECTED)

    load_runtime_entry_points(descriptors, disabled_ids=frozenset({"atlas.search"}))

    assert not runtime.is_active()
    # `disconnect` reports whether a receiver with that uid was connected.
    assert post_save.disconnect(dispatch_uid="atlas_plugin_search.save") is False
    make_note("alpha")
    assert PendingChange.objects.count() == 0


def test_enabled_plugin_runs_the_whole_startup_sequence(db, engine, source, make_note):
    register_search_source(source, owner="test.source")
    register_search_engine(engine, owner="test.engine")
    descriptors = load_selected_descriptors(_SELECTED)

    load_runtime_entry_points(descriptors)

    assert runtime.is_active()
    make_note("alpha")
    assert PendingChange.objects.count() == 1
