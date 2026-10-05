"""Plugin search sources end to end (`add-search-sources`): a content edit is
queued by the model signal, indexed by a drain and found through the real HTTP
endpoint; nothing is faked except test data.
"""

import pytest
from atlas_plugin_api import (
    get_search_source_lookup,
    register_search_engine,
    register_search_source,
)
from atlas_plugin_api import search as search_contract
from atlas_plugin_api.permissions import registry as permission_registry
from atlas_plugin_apis import openapi_import
from atlas_plugin_apis.models import ApiDetails, ApiEndpoint, ApiOperation
from atlas_plugin_apis.search_source import api_search_source
from atlas_plugin_database_schema.search_source import (
    database_schema_search_source,
)
from atlas_plugin_flows.models import Flow
from atlas_plugin_flows.search_source import flow_search_source
from atlas_plugin_search import indexer, plugin, runtime, signals
from atlas_plugin_search_postgres.engine import PostgresSearchEngine

from server.apps.catalog.search_source import catalog_search_source
from server.apps.catalog.services.entity_service import EntityService
from server.apps.catalog.tests.factories import create_api, create_resource

pytestmark = pytest.mark.django_db

SEARCH = "/api/plugins/atlas.search/search/"


SOURCES = (
    (catalog_search_source, "atlas.catalog"),
    (flow_search_source, "atlas.flows"),
    (api_search_source, "atlas.apis"),
    (database_schema_search_source, "atlas.database-schema"),
)


def _reset_search_state():
    search_contract._search_source_registry.__init__()
    search_contract._search_engine_registry.__init__()
    permission_registry._owners.pop(plugin.STATUS_ADMIN_PERMISSION, None)
    permission_registry._effects.pop(plugin.STATUS_ADMIN_PERMISSION, None)
    runtime.reset()
    signals.disconnect()


@pytest.fixture(autouse=True)
def search_active():
    """Make sure search is running with all the real sources and the engine.

    Other test modules leave the process-wide registries in different states
    (another module may have activated search with fewer sources), so start
    from a known state unless it already is the one needed.
    """
    lookup = get_search_source_lookup()
    if not runtime.is_active() or any(
        lookup.get(s.id) is None for s, _ in SOURCES
    ):
        _reset_search_state()
        for source, owner in SOURCES:
            register_search_source(source, owner=owner)
        register_search_engine(
            PostgresSearchEngine(), owner="atlas.search-postgres"
        )
        plugin.register_runtime()
        plugin.finalize_runtime()
    indexer.rebuild_index()


def _ids(client, text, kind=None):
    params = {"q": text}
    if kind:
        params["kinds"] = kind
    response = client.get(SEARCH, data=params)
    assert response.status_code == 200
    return [result["id"] for result in response.json()["results"]]


# --- flows -------------------------------------------------------------------


def test_flow_rename_and_delete_reach_the_index(superuser_client, system):
    flow = Flow.objects.create(system=system, name="zebracorn-saga")
    doc_id = f"flow:{flow.pk}"
    indexer.drain_pending()
    assert _ids(superuser_client, "zebracorn") == [doc_id]

    flow.name = "quokkaforge-saga"
    flow.save()
    indexer.drain_pending()
    assert _ids(superuser_client, "zebracorn") == []
    assert _ids(superuser_client, "quokkaforge") == [doc_id]

    flow.delete()
    indexer.drain_pending()
    assert _ids(superuser_client, "quokkaforge") == []


def test_flow_step_text_is_found_and_edits_to_it_reindex(
    superuser_client, system
):
    flow = Flow.objects.create(
        system=system,
        name="checkout",
        steps=[{"id": "a", "external_label": "Zebracorn gateway"}],
    )
    indexer.drain_pending()
    assert _ids(superuser_client, "zebracorn") == [f"flow:{flow.pk}"]

    flow.steps = [{"id": "a", "external_label": "Quokkaforge gateway"}]
    flow.save()
    indexer.drain_pending()
    assert _ids(superuser_client, "zebracorn") == []
    assert _ids(superuser_client, "quokkaforge") == [f"flow:{flow.pk}"]


def test_removing_the_owning_system_removes_its_flows(
    superuser_client, superuser_account, system
):
    flow = Flow.objects.create(system=system, name="zebracorn-saga")
    indexer.drain_pending()
    assert _ids(superuser_client, "zebracorn") == [f"flow:{flow.pk}"]

    EntityService().remove(entity_id=system.pk, actor=superuser_account)
    indexer.drain_pending()

    assert _ids(superuser_client, "zebracorn") == []


# --- apis --------------------------------------------------------------------


@pytest.fixture
def api(group, system):
    return create_api(name="orders-api", owner=group, system=system)


def test_endpoint_is_found_by_path_and_operation_id(superuser_client, api):
    endpoint = ApiEndpoint.objects.create(
        api=api,
        method="GET",
        path="/zebracorn/{id}",
        operation_id="getQuokkaforge",
    )
    doc_id = f"endpoint:{endpoint.pk}"
    indexer.drain_pending()

    assert _ids(superuser_client, "zebracorn") == [doc_id]
    assert _ids(superuser_client, "getQuokkaforge") == [doc_id]
    assert _ids(superuser_client, "zebracorn", kind="endpoint") == [doc_id]


def test_operation_is_found_by_channel_address(superuser_client, api):
    operation = ApiOperation.objects.create(
        api=api,
        channel_address="orders.zebracorn.created",
        direction="send",
        operation_key="k",
    )
    indexer.drain_pending()

    assert _ids(superuser_client, "zebracorn") == [f"operation:{operation.pk}"]


def test_removed_endpoint_disappears_and_restored_endpoint_returns(
    superuser_client, api
):
    endpoint = ApiEndpoint.objects.create(
        api=api, method="GET", path="/zebracorn"
    )
    doc_id = f"endpoint:{endpoint.pk}"
    indexer.drain_pending()
    assert _ids(superuser_client, "zebracorn") == [doc_id]

    endpoint.status = ApiEndpoint.STATUS_REMOVED
    endpoint.save()
    indexer.drain_pending()
    assert _ids(superuser_client, "zebracorn") == []

    endpoint.status = ApiEndpoint.STATUS_ACTIVE
    endpoint.save()
    indexer.drain_pending()
    assert _ids(superuser_client, "zebracorn") == [doc_id]


def test_endpoint_dropped_from_a_resynced_spec_disappears(
    superuser_client, api
):
    endpoint = ApiEndpoint.objects.create(
        api=api, method="GET", path="/zebracorn"
    )
    indexer.drain_pending()
    assert _ids(superuser_client, "zebracorn") == [f"endpoint:{endpoint.pk}"]

    openapi_import._upsert_operations(api, [])
    indexer.drain_pending()

    assert _ids(superuser_client, "zebracorn") == []


def test_text_only_in_a_raw_specification_finds_nothing(superuser_client, api):
    ApiEndpoint.objects.create(api=api, method="GET", path="/pets")
    ApiDetails.objects.filter(entity=api).update(
        spec_content="x-note: rawspectoken"
    )
    indexer.drain_pending()
    indexer.rebuild_index()

    assert _ids(superuser_client, "rawspectoken") == []


# --- database schemas ---------------------------------------------------------


@pytest.fixture
def resource(group):
    return create_resource(name="zebracorn-db", owner=group, type="database")


def _schema_url(resource):
    return f"/api/plugins/atlas.database-schema/resources/{resource.pk}/schema/"


def test_schema_edit_is_found_by_new_table_and_column_names(
    superuser_client, resource
):
    url = _schema_url(resource)
    created = superuser_client.post(
        url,
        {"dialect": "postgresql", "source_sql": "CREATE TABLE pets (id int);"},
    )
    assert created.status_code == 201
    doc_id = f"schema:{resource.pk}"
    indexer.drain_pending()
    assert _ids(superuser_client, "pets", kind="schema") == [doc_id]
    assert _ids(superuser_client, "quokkaforge") == []

    edited = superuser_client.patch(
        url,
        {
            "source_sql": "CREATE TABLE pets (id int, quokkaforge_tag text);"
            "CREATE TABLE owners (id int);"
        },
    )
    assert edited.status_code == 200
    indexer.drain_pending()

    assert _ids(superuser_client, "quokkaforge") == [doc_id]
    assert _ids(superuser_client, "tag") == [doc_id]
    assert _ids(superuser_client, "owners") == [doc_id]


def test_owner_rename_refreshes_the_schema_title(superuser_client, resource):
    superuser_client.post(
        _schema_url(resource),
        {"dialect": "postgresql", "source_sql": "CREATE TABLE pets (id int);"},
    )
    indexer.drain_pending()
    assert _ids(superuser_client, "zebracorn", kind="schema") == [
        f"schema:{resource.pk}"
    ]

    resource.name = "quokkaforge-db"
    resource.save()
    indexer.drain_pending()

    assert _ids(superuser_client, "zebracorn", kind="schema") == []
    assert _ids(superuser_client, "quokkaforge", kind="schema") == [
        f"schema:{resource.pk}"
    ]


def test_failed_parse_is_still_found_by_the_owner_name(
    superuser_client, resource
):
    created = superuser_client.post(
        _schema_url(resource),
        {"dialect": "postgresql", "source_sql": "this is not sql"},
    )
    assert created.json()["parseStatus"] == "failed"
    indexer.drain_pending()

    assert _ids(superuser_client, "zebracorn", kind="schema") == [
        f"schema:{resource.pk}"
    ]
    assert _ids(superuser_client, "pets") == []


# --- labels and links ---------------------------------------------------------


def test_every_new_kind_has_a_label_and_a_link_the_dialog_can_open(
    superuser_client, api, system, resource
):
    flow = Flow.objects.create(system=system, name="zebracorn-flow")
    endpoint = ApiEndpoint.objects.create(
        api=api, method="GET", path="/zebracorn"
    )
    operation = ApiOperation.objects.create(
        api=api,
        channel_address="zebracorn.created",
        direction="send",
        operation_key="k",
    )
    superuser_client.post(
        _schema_url(resource),
        {
            "dialect": "postgresql",
            "source_sql": "CREATE TABLE zebracorn (id int);",
        },
    )
    indexer.drain_pending()

    response = superuser_client.get(
        SEARCH, data={"q": "zebracorn", "pageSize": 50}
    )
    results = {r["id"]: r for r in response.json()["results"]}

    expected = {
        f"flow:{flow.pk}": ("Flow", f"/flows/{flow.pk}"),
        f"endpoint:{endpoint.pk}": (
            "Endpoint",
            f"/apis/{api.pk}/endpoints/{endpoint.pk}",
        ),
        f"operation:{operation.pk}": (
            "Operation",
            f"/apis/{api.pk}/operations/{operation.pk}",
        ),
        f"schema:{resource.pk}": (
            "Database schema",
            f"/resources/{resource.pk}?tab=schema",
        ),
    }
    for document_id, (label, link) in expected.items():
        assert results[document_id]["kindLabel"] == label
        assert results[document_id]["link"] == link
