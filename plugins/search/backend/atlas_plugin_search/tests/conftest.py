"""Fixtures for the search plugin's tests.

This tree is separate from `core/backend`, so its conftest is not inherited:
the few fixtures needed are defined here.
"""

import pytest
from atlas_plugin_api import search as search_contract
from atlas_plugin_api.permissions import registry as permission_registry
from django.contrib.auth import get_user_model
from server.apps.catalog.tests.factories import create_group

from atlas_plugin_search import plugin, runtime, signals
from atlas_plugin_search.config import SearchPluginConfig
from atlas_plugin_search.tests.fakes import CatalogNoteSource, FakeEngine


def _reset_search_state() -> None:
    search_contract._search_source_registry.__init__()
    search_contract._search_engine_registry.__init__()
    permission_registry._owners.pop(plugin.STATUS_ADMIN_PERMISSION, None)
    permission_registry._effects.pop(plugin.STATUS_ADMIN_PERMISSION, None)
    search_contract.configure_search_body_limit(None)
    runtime.reset()
    signals.disconnect()


@pytest.fixture(autouse=True)
def clean_search_runtime():
    """Every test starts with empty registries and an inactive plugin."""
    _reset_search_state()
    yield
    _reset_search_state()


@pytest.fixture
def engine() -> FakeEngine:
    return FakeEngine()


@pytest.fixture
def source() -> CatalogNoteSource:
    return CatalogNoteSource()


@pytest.fixture
def activate(db, engine, source):
    """Start the plugin the way core does: register, then finalize."""

    def _activate(config: SearchPluginConfig | None = None):
        search_contract.register_search_source(source, owner="test.source")
        search_contract.register_search_engine(engine, owner="test.engine")
        plugin.register_runtime()
        if config is not None:
            runtime.configure(config)
        plugin.finalize_runtime()

    return _activate


@pytest.fixture
def active(activate):
    activate()


@pytest.fixture
def make_note(db):
    def _make(name: str, description: str = ""):
        return create_group(name=name, description=description)

    return _make


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(username="user", password="password123")


@pytest.fixture
def superuser(db):
    return get_user_model().objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="password123",
    )


@pytest.fixture
def user_client(dmr_client, user):
    dmr_client.force_login(user)
    return dmr_client


@pytest.fixture
def superuser_client(dmr_client, superuser):
    dmr_client.force_login(superuser)
    return dmr_client
