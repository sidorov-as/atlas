"""Flows, API endpoints/operations and database schemas, found end to end.

Each test edits content through its model, runs an indexing pass and finds it
through the search endpoint, using the real sources of the three plugins and
the PostgreSQL engine (`search-source` change, task 7.1). Lives with core's
tests because it spans several plugins, which may not import each other.
"""

import pytest
from atlas_plugin_api import register_search_engine, register_search_source
from atlas_plugin_api import search as search_contract
from atlas_plugin_api.permissions import registry as permission_registry
from atlas_plugin_apis.models import ApiEndpoint, ApiOperation
from atlas_plugin_apis.search_source import api_search_source
from atlas_plugin_database_schema.models import DatabaseSchema
from atlas_plugin_database_schema.parser import parse_schema
from atlas_plugin_database_schema.search_source import (
    database_schema_search_source,
)
from atlas_plugin_flows.models import Flow
from atlas_plugin_flows.search_source import flow_search_source
from atlas_plugin_search import indexer, plugin, runtime, signals
from atlas_plugin_search_postgres.engine import PostgresSearchEngine

from server.apps.catalog.tests.factories import (
    create_api,
    create_resource,
    create_system,
)

SEARCH = "/api/plugins/atlas.search/search/"


def _reset() -> None:
    search_contract._search_source_registry.__init__()
    search_contract._search_engine_registry.__init__()
    permission_registry._owners.pop(plugin.STATUS_ADMIN_PERMISSION, None)
    permission_registry._effects.pop(plugin.STATUS_ADMIN_PERMISSION, None)
    search_contract.configure_search_body_limit(None)
    runtime.reset()
    signals.disconnect()


@pytest.fixture(autouse=True)
def search_started(db):
    """Start the search plugin with the three content sources registered."""
    _reset()
    for source, owner in (
        (flow_search_source, "atlas.flows"),
        (api_search_source, "atlas.apis"),
        (database_schema_search_source, "atlas.database-schema"),
    ):
        register_search_source(source, owner=owner)
    register_search_engine(
        PostgresSearchEngine(), owner="atlas.search-postgres"
    )
    plugin.register_runtime()
    plugin.finalize_runtime()
    yield
    _reset()


@pytest.fixture
def system(group):
    return create_system(name="booking", owner=group)


@pytest.fixture
def api(group, system):
    return create_api(name="orders-api", owner=group, system=system)


@pytest.fixture
def client(owner_client):
    return owner_client


def _find(client, query: str, **params) -> list[dict]:
    indexer.drain_pending()
    response = client.get(SEARCH, data={"q": query, **params})
    assert response.status_code == 200
    return response.json()["results"]


def _ids(results) -> list[str]:
    return [r["id"] for r in results]


def test_flow_is_found_by_its_step_text_and_follows_edits(client, system):
    flow = Flow.objects.create(
        system=system,
        name="checkout-saga",
        steps=[{"id": "a", "title": "Reserve stock"}],
    )

    [hit] = _find(client, "reserve")
    assert hit["id"] == f"flow:{flow.pk}"
    assert hit["kind"] == "flow"
    assert hit["kindLabel"] == "Flow"
    assert hit["link"] == f"/flows/{flow.pk}"

    flow.steps = [{"id": "a", "title": "Quokkaforge gateway"}]
    flow.save()

    assert _find(client, "reserve") == []
    assert _ids(_find(client, "quokkaforge")) == [f"flow:{flow.pk}"]

    flow.delete()

    assert _find(client, "quokkaforge") == []


def test_endpoint_and_operation_are_found_by_path_and_channel(client, api):
    endpoint = ApiEndpoint.objects.create(
        api=api,
        method="GET",
        path="/zebracorn/{id}",
        summary="Fetch a zebracorn",
    )
    operation = ApiOperation.objects.create(
        api=api,
        channel_address="orders.quokkaforge.created",
        direction="send",
        operation_key="sendOrderCreated",
        operation_id="sendOrderCreated",
        summary="Announce a new order",
    )

    assert _ids(_find(client, "zebracorn")) == [f"endpoint:{endpoint.pk}"]
    assert _ids(_find(client, "quokkaforge")) == [f"operation:{operation.pk}"]
    assert _ids(_find(client, "zebracorn", kinds="operation")) == []

    endpoint.summary = "Fetch a pangolin"
    endpoint.save()

    assert _ids(_find(client, "pangolin")) == [f"endpoint:{endpoint.pk}"]


def test_schema_is_found_by_table_and_column_names_and_owner_title(
    client, group
):
    resource = create_resource(name="primary-db", owner=group, type="database")
    sql = (
        "CREATE TABLE order_items (id uuid PRIMARY KEY, sku_code varchar(20));"
    )
    DatabaseSchema.objects.create(
        entity=resource,
        source_sql=sql,
        parsed_schema=parse_schema(sql, "postgresql"),
    )

    [hit] = _find(client, "sku_code")
    assert hit["id"] == f"schema:{resource.pk}"
    assert hit["kind"] == "schema"
    assert hit["kindLabel"] == "Database schema"
    assert hit["title"] == "primary-db"

    resource.name = "ledger-db"
    resource.save()

    assert _find(client, "primary") == []
    assert [r["title"] for r in _find(client, "ledger")] == ["ledger-db"]


def test_search_spans_all_content_types_with_the_kind_filter(
    client, system, api
):
    flow = Flow.objects.create(system=system, name="warehouse flow")
    endpoint = ApiEndpoint.objects.create(
        api=api, method="GET", path="/warehouse", summary=""
    )

    assert sorted(_ids(_find(client, "warehouse"))) == sorted(
        [f"flow:{flow.pk}", f"endpoint:{endpoint.pk}"]
    )
    assert _ids(_find(client, "warehouse", kinds="flow")) == [f"flow:{flow.pk}"]


def test_full_rebuild_indexes_existing_content(client, system):
    flow = Flow.objects.create(system=system, name="legacy flow")
    indexer.drain_pending()
    runtime.get_engine().delete([f"flow:{flow.pk}"])
    assert _find(client, "legacy") == []

    indexer.rebuild_index()

    assert _ids(_find(client, "legacy")) == [f"flow:{flow.pk}"]


def test_without_the_search_plugin_edits_record_nothing(system, api, group):
    """A distribution without search registers the sources and nothing else."""
    from atlas_plugin_search.models import PendingChange

    signals.disconnect()
    runtime.reset()

    flow = Flow.objects.create(system=system, name="plain flow")
    flow.name = "renamed flow"
    flow.save()
    ApiEndpoint.objects.create(api=api, method="GET", path="/plain", summary="")
    resource = create_resource(name="plain-db", owner=group, type="database")
    DatabaseSchema.objects.create(
        entity=resource, source_sql="", parsed_schema={}
    )
    flow.delete()

    assert not runtime.is_active()
    assert PendingChange.objects.count() == 0
