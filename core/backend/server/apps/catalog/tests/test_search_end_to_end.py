"""Search end to end: catalog source, indexer and PostgreSQL engine behind the
real HTTP endpoint (`search-indexing` / `search-api` specs).

Nothing is faked: a catalog write queues a pending change through the model
signal, the drain indexes it, and results come out of `resolve`.
"""

import pytest
from atlas_plugin_api import (
    get_search_engine_lookup,
    get_search_source_lookup,
    register_search_engine,
    register_search_source,
)
from atlas_plugin_search import indexer, plugin, runtime
from atlas_plugin_search.models import PendingChange
from atlas_plugin_search_postgres.engine import PostgresSearchEngine

from server.apps.catalog.search_source import catalog_search_source
from server.apps.catalog.services.entity_service import EntityService
from server.apps.catalog.tests.factories import create_system

pytestmark = pytest.mark.django_db

SEARCH = "/api/plugins/atlas.search/search/"


@pytest.fixture(autouse=True)
def search_active():
    """Make sure search is running with the real source and engine.

    The plugin's own tests reset the process-wide registries; start from a
    known state whatever ran before.
    """
    if not runtime.is_active():
        if get_search_source_lookup().get(catalog_search_source.id) is None:
            register_search_source(catalog_search_source, owner="atlas.catalog")
        if not get_search_engine_lookup().all():
            register_search_engine(
                PostgresSearchEngine(), owner="atlas.search-postgres"
            )
        plugin.register_runtime()
        plugin.finalize_runtime()
    indexer.rebuild_index()


def _ids(client, text):
    response = client.get(SEARCH, data={"q": text})
    assert response.status_code == 200
    return [result["id"] for result in response.json()["results"]]


def test_edit_is_searchable_after_a_drain_and_removal_makes_it_disappear(
    superuser_client, superuser_account, group
):
    system = create_system(name="zebracorn", owner=group, description="Ledger")
    doc_id = f"system:{system.pk}"

    # Written but not drained: queued, not yet searchable.
    assert PendingChange.objects.filter(document_id=doc_id).exists()
    assert _ids(superuser_client, "zebracorn") == []

    indexer.drain_pending()

    assert not PendingChange.objects.filter(document_id=doc_id).exists()
    assert _ids(superuser_client, "zebracorn") == [doc_id]

    # An edit is picked up by the next drain: the old name stops matching.
    system.name = "quokkaforge"
    system.save()
    indexer.drain_pending()

    assert _ids(superuser_client, "zebracorn") == []
    assert _ids(superuser_client, "quokkaforge") == [doc_id]

    # Removing the entity deletes it from the index and from results.
    EntityService().remove(entity_id=system.pk, actor=superuser_account)
    indexer.drain_pending()

    assert _ids(superuser_client, "quokkaforge") == []
    assert not PendingChange.objects.filter(document_id=doc_id).exists()
