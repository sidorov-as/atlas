"""Switching the search engine and rebuilding keeps the same UI contract.

The same catalog is searched through the same endpoint first with the
PostgreSQL adapter, then, after a rebuild, with the Meilisearch adapter, and
back again (`search-meilisearch-engine` spec: "Selected instead of the default
engine"). Lives with core's tests because it spans the search plugin and both
adapters, which may not import each other. Needs a real instance: see the
Meilisearch adapter's `tests/conftest.py`.
"""

import os
import uuid

import pytest
from atlas_plugin_api import register_search_engine, register_search_source
from atlas_plugin_api import search as search_contract
from atlas_plugin_api.permissions import registry as permission_registry
from atlas_plugin_search import indexer, plugin, runtime, signals
from atlas_plugin_search_meilisearch.client import MeilisearchClient
from atlas_plugin_search_meilisearch.config import SearchMeilisearchPluginConfig
from atlas_plugin_search_meilisearch.engine import MeilisearchSearchEngine
from atlas_plugin_search_postgres.engine import PostgresSearchEngine

from server.apps.catalog.search_source import catalog_search_source
from server.apps.catalog.tests.factories import create_system

pytestmark = pytest.mark.django_db

SEARCH = "/api/plugins/atlas.search/search/"
STATUS = "/api/plugins/atlas.search/status/"
POSTGRES = "atlas.search-postgres"
MEILI = "atlas.search-meilisearch"


def _reset_search_state() -> None:
    search_contract._search_source_registry.__init__()
    search_contract._search_engine_registry.__init__()
    permission_registry._owners.pop(plugin.STATUS_ADMIN_PERMISSION, None)
    permission_registry._effects.pop(plugin.STATUS_ADMIN_PERMISSION, None)
    search_contract.configure_search_body_limit(None)
    runtime.reset()
    signals.disconnect()


def _meili_config() -> SearchMeilisearchPluginConfig:
    url = os.environ.get("ATLAS_TEST_MEILISEARCH_URL")
    if not url:
        if os.environ.get("ATLAS_REQUIRE_MEILISEARCH"):
            pytest.fail("ATLAS_TEST_MEILISEARCH_URL is required but not set")
        pytest.skip("ATLAS_TEST_MEILISEARCH_URL is not set")
    return SearchMeilisearchPluginConfig(
        url=url,
        key=os.environ.get("ATLAS_TEST_MEILISEARCH_KEY") or None,
        index=f"atlas-switch-{uuid.uuid4().hex[:12]}",
        taskTimeoutSeconds=30,
    )


@pytest.fixture
def switch_engine():
    """Restart search with exactly one engine selected, as a redeploy would."""
    meili = _meili_config()
    engines = {
        POSTGRES: lambda: PostgresSearchEngine(),
        MEILI: lambda: MeilisearchSearchEngine(meili),
    }

    def _switch(engine_id: str) -> None:
        _reset_search_state()
        register_search_source(catalog_search_source, owner="atlas.catalog")
        register_search_engine(engines[engine_id](), owner=engine_id)
        plugin.register_runtime()
        plugin.finalize_runtime()
        assert runtime.get_engine().id == engines[engine_id]().id

    yield _switch

    _reset_search_state()
    MeilisearchClient(
        meili.url, meili.key, request_timeout=10, task_timeout=30
    ).request("DELETE", f"/indexes/{meili.index}")


def _search(client, text):
    response = client.get(SEARCH, data={"q": text})
    assert response.status_code == 200
    return response.json()["results"]


def _ids(client, text):
    return [result["id"] for result in _search(client, text)]


def test_switching_engines_and_rebuilding_serves_the_same_results(
    switch_engine, superuser_client, group
):
    zebra = create_system(name="zebracorn", owner=group, description="Ledger")
    create_system(
        name="quokkaforge", owner=group, description="Mentions zebracorn"
    )
    zebra_id = f"system:{zebra.pk}"

    switch_engine(POSTGRES)
    indexed = indexer.rebuild_index()
    postgres_results = _search(superuser_client, "zebracorn")
    assert postgres_results[0]["id"] == zebra_id  # title match first
    assert len(postgres_results) == 2

    # Switching alone does not carry the index over: the new engine is empty.
    switch_engine(MEILI)
    assert _ids(superuser_client, "zebracorn") == []

    # The rebuild fills it, and the same endpoint answers the same way.
    assert indexer.rebuild_index() == indexed
    meili_results = _search(superuser_client, "zebracorn")
    assert [r["id"] for r in meili_results] == [
        r["id"] for r in postgres_results
    ]
    assert set(meili_results[0]) == set(postgres_results[0])

    # Meilisearch-only behaviour behind the same endpoint: typo tolerance.
    assert _ids(superuser_client, "zebracron")[0] == zebra_id

    # Edits reach the new engine through the ordinary drain.
    zebra.name = "narwhalworks"
    zebra.save()
    indexer.drain_pending()
    assert _ids(superuser_client, "narwhalworks")[0] == zebra_id

    # Going back is the same procedure: select, rebuild.
    switch_engine(POSTGRES)
    indexer.rebuild_index()
    assert _ids(superuser_client, "narwhalworks")[0] == zebra_id


def test_status_reports_the_selected_engine_after_a_switch(
    switch_engine, superuser_client, group
):
    create_system(name="zebracorn", owner=group)

    expected = None
    for engine_id, engine_name in (
        (POSTGRES, "postgres"),
        (MEILI, "meilisearch"),
    ):
        switch_engine(engine_id)
        count = indexer.rebuild_index()
        expected = count if expected is None else expected
        response = superuser_client.get(STATUS)
        assert response.status_code == 200
        body = response.json()
        assert body["engine"] == engine_name
        assert body["documentCount"] == count == expected
