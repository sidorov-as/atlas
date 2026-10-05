import pytest
from atlas_plugin_api import SearchEngineSelectionError, register_search_engine

from atlas_plugin_search import plugin, runtime
from atlas_plugin_search.config import SearchPluginConfig
from atlas_plugin_search.job_ids import (
    DRAIN_JOB_ID,
    INITIAL_REBUILD_JOB_ID,
    REBUILD_JOB_ID,
)
from atlas_plugin_search.tests.fakes import FakeEngine


def test_descriptor_declares_every_job_id_and_the_config_schema():
    assert set(plugin.PLUGIN.job_ids) == {
        DRAIN_JOB_ID,
        REBUILD_JOB_ID,
        INITIAL_REBUILD_JOB_ID,
    }
    assert plugin.PLUGIN.config_schema is SearchPluginConfig
    assert plugin.PLUGIN.django_apps == ("atlas_plugin_search",)


def test_config_defaults_and_engine_setting():
    config = SearchPluginConfig()
    assert config.engine is None
    assert config.drain_interval_seconds == 10
    assert config.rebuild_interval_seconds == 6 * 60 * 60
    assert SearchPluginConfig(engine="atlas.search-postgres").engine == (
        "atlas.search-postgres"
    )
    with pytest.raises(ValueError):
        SearchPluginConfig(drainIntervalSeconds=0)


def test_register_runtime_alone_does_not_activate_the_plugin():
    plugin.register_runtime()

    assert not runtime.is_active()


def test_finalize_fails_when_no_engine_is_registered():
    plugin.register_runtime()

    with pytest.raises(SearchEngineSelectionError, match="engine plugin"):
        plugin.finalize_runtime()
    assert not runtime.is_active()


def test_finalize_uses_the_only_engine(engine):
    register_search_engine(engine, owner="test.engine")
    plugin.register_runtime()

    plugin.finalize_runtime()

    assert runtime.is_active()
    assert runtime.get_engine() is engine


def test_finalize_sees_an_engine_registered_after_register_runtime(engine):
    # Manifest order: search first, engine plugin second.
    plugin.register_runtime()
    register_search_engine(engine, owner="test.engine")

    plugin.finalize_runtime()

    assert runtime.get_engine() is engine


def test_two_engines_without_setting_fail_listing_both():
    register_search_engine(FakeEngine("one"), owner="plugin.one")
    register_search_engine(FakeEngine("two"), owner="plugin.two")
    plugin.register_runtime()

    with pytest.raises(SearchEngineSelectionError, match="one.*two|two.*one"):
        plugin.finalize_runtime()


def test_two_engines_with_setting_pick_that_plugins_engine():
    first, second = FakeEngine("one"), FakeEngine("two")
    register_search_engine(first, owner="plugin.one")
    register_search_engine(second, owner="plugin.two")
    plugin.register_runtime()
    runtime.configure(SearchPluginConfig(engine="plugin.two"))

    plugin.finalize_runtime()

    assert runtime.get_engine() is second


def test_setting_naming_another_plugin_than_the_only_engine_fails(engine):
    register_search_engine(engine, owner="test.engine")
    plugin.register_runtime()
    runtime.configure(SearchPluginConfig(engine="plugin.other"))

    with pytest.raises(SearchEngineSelectionError, match="plugin.other"):
        plugin.finalize_runtime()


def test_register_runtime_applies_the_body_limit(monkeypatch):
    seen = []
    monkeypatch.setattr("atlas_plugin_api.configure_search_body_limit", seen.append)
    monkeypatch.setattr(
        "atlas_plugin_api.get_plugin_config",
        lambda plugin_id, schema: SearchPluginConfig(maxBodyChars=500),
    )

    plugin.register_runtime()

    assert seen == [500]


def test_register_runtime_registers_the_admin_permission():
    from atlas_plugin_api.permissions import registry

    plugin.register_runtime()

    assert registry.effect_for(plugin.STATUS_ADMIN_PERMISSION) == "read"
