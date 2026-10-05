"""Meilisearch failures seen through the search drain job.

A write that the engine rejects, never finishes, or cannot receive must leave
its pending change queued and be recorded in the index status, and the next
drain must index it once the engine recovers (`search-meilisearch-engine`
spec: "Writes complete before success is reported"). Lives with core's tests
because it spans the search plugin and the adapter, which may not import each
other. Needs a real instance: see the adapter's `tests/conftest.py`.
"""

import os
import uuid

import pytest
from atlas_plugin_api import register_search_engine, register_search_source
from atlas_plugin_api import search as search_contract
from atlas_plugin_api.permissions import registry as permission_registry
from atlas_plugin_search import indexer, jobs, plugin, runtime, signals
from atlas_plugin_search.models import IndexStatus, PendingChange
from atlas_plugin_search_meilisearch import client as meili_client
from atlas_plugin_search_meilisearch.client import MeilisearchClient
from atlas_plugin_search_meilisearch.config import SearchMeilisearchPluginConfig
from atlas_plugin_search_meilisearch.engine import MeilisearchSearchEngine

from server.apps.catalog.search_source import catalog_search_source
from server.apps.catalog.tests.factories import create_system

pytestmark = pytest.mark.django_db

SEARCH = "/api/plugins/atlas.search/search/"
DEAD_URL = "http://127.0.0.1:9"  # the discard port: nothing listens there


def _reset_search_state() -> None:
    search_contract._search_source_registry.__init__()
    search_contract._search_engine_registry.__init__()
    permission_registry._owners.pop(plugin.STATUS_ADMIN_PERMISSION, None)
    permission_registry._effects.pop(plugin.STATUS_ADMIN_PERMISSION, None)
    search_contract.configure_search_body_limit(None)
    runtime.reset()
    signals.disconnect()


def _config(**overrides) -> SearchMeilisearchPluginConfig:
    url = os.environ.get("ATLAS_TEST_MEILISEARCH_URL")
    if not url:
        if os.environ.get("ATLAS_REQUIRE_MEILISEARCH"):
            pytest.fail("ATLAS_TEST_MEILISEARCH_URL is required but not set")
        pytest.skip("ATLAS_TEST_MEILISEARCH_URL is not set")
    values = {
        "url": url,
        "key": os.environ.get("ATLAS_TEST_MEILISEARCH_KEY") or None,
        "index": f"atlas-drain-{uuid.uuid4().hex[:12]}",
        "taskTimeoutSeconds": 30,
        "requestTimeoutSeconds": 5,
    } | overrides
    return SearchMeilisearchPluginConfig(**values)


@pytest.fixture
def start_search():
    """Start the search plugin with the adapter built from `config`."""
    started: list[SearchMeilisearchPluginConfig] = []

    def _start(
        config: SearchMeilisearchPluginConfig,
    ) -> MeilisearchSearchEngine:
        _reset_search_state()
        engine = MeilisearchSearchEngine(config)
        register_search_source(catalog_search_source, owner="atlas.catalog")
        register_search_engine(engine, owner="atlas.search-meilisearch")
        plugin.register_runtime()
        plugin.finalize_runtime()
        started.append(config)
        return engine

    yield _start

    _reset_search_state()
    for config in started:
        real = _config()
        if config.url == real.url:
            MeilisearchClient(
                real.url, real.key, request_timeout=10, task_timeout=30
            ).request("DELETE", f"/indexes/{config.index}")


def _ids(client, text):
    response = client.get(SEARCH, data={"q": text})
    assert response.status_code == 200
    return [result["id"] for result in response.json()["results"]]


def _pending_ids():
    return set(PendingChange.objects.values_list("document_id", flat=True))


def _last_error():
    status = IndexStatus.objects.get()
    return status.last_error, status.last_error_job


def test_drain_indexes_changes_through_meilisearch(
    start_search, superuser_client, group
):
    start_search(_config())
    system = create_system(name="zebracorn", owner=group, description="Ledger")

    result = jobs.drain_job()

    assert result is None
    assert _pending_ids() == set()
    assert _ids(superuser_client, "zebracorn") == [f"system:{system.pk}"]


def test_a_task_the_engine_marks_failed_keeps_the_change_pending(
    start_search, superuser_client, group, monkeypatch
):
    engine = start_search(_config())
    system = create_system(name="zebracorn", owner=group)
    doc_id = f"system:{system.pk}"
    real_request = engine._client.request

    def failing_tasks(method, path, **kwargs):
        if method == "GET" and path.startswith("/tasks/"):
            return {
                "status": "failed",
                "error": {"code": "invalid_document_id", "message": "rejected"},
            }
        return real_request(method, path, **kwargs)

    monkeypatch.setattr(engine._client, "request", failing_tasks)

    jobs.drain_job()

    assert _pending_ids() == {doc_id}
    message, job = _last_error()
    assert job == indexer.DRAIN
    assert "invalid_document_id" in message

    # Once the engine accepts writes again, the same pending change is indexed.
    monkeypatch.setattr(engine._client, "request", real_request)
    jobs.drain_job()

    assert _pending_ids() == set()
    assert _ids(superuser_client, "zebracorn") == [doc_id]
    assert _last_error() == ("", "")


def test_a_task_that_does_not_finish_in_time_keeps_the_change_pending(
    start_search, group, monkeypatch
):
    engine = start_search(_config(taskTimeoutSeconds=0.3))
    system = create_system(name="zebracorn", owner=group)
    real_request = engine._client.request

    def never_finishes(method, path, **kwargs):
        if method == "GET" and path.startswith("/tasks/"):
            return {"status": "processing"}
        return real_request(method, path, **kwargs)

    monkeypatch.setattr(engine._client, "request", never_finishes)
    monkeypatch.setattr(meili_client.time, "sleep", lambda _: None)

    jobs.drain_job()

    assert _pending_ids() == {f"system:{system.pk}"}
    message, job = _last_error()
    assert job == indexer.DRAIN
    assert "did not finish" in message


def test_an_unreachable_instance_keeps_changes_pending_and_never_raises(
    start_search, group
):
    start_search(_config(url=DEAD_URL, key=None, requestTimeoutSeconds=1))
    system = create_system(name="zebracorn", owner=group)

    jobs.drain_job()  # must swallow the failure like any scheduled job

    assert _pending_ids() == {f"system:{system.pk}"}
    message, job = _last_error()
    assert job == indexer.DRAIN
    assert "unreachable" in message


def test_a_rejected_access_key_is_reported_without_the_key(start_search, group):
    config = _config(key="a-wrong-key-with-enough-length")
    if not os.environ.get("ATLAS_TEST_MEILISEARCH_KEY"):
        pytest.skip("the instance enforces no key")
    start_search(config)
    system = create_system(name="zebracorn", owner=group)

    jobs.drain_job()

    assert _pending_ids() == {f"system:{system.pk}"}
    message, _ = _last_error()
    assert "access key" in message
    assert "a-wrong-key-with-enough-length" not in message


def test_status_and_search_report_an_unreachable_instance(
    start_search, superuser_client
):
    engine = start_search(
        _config(url=DEAD_URL, key=None, requestTimeoutSeconds=1)
    )

    health = engine.health()

    assert not health.ok
    assert "unreachable" in health.detail
    response = superuser_client.get(SEARCH, data={"q": "anything"})
    assert response.status_code == 503


def test_a_failed_rebuild_is_recorded_and_the_live_index_is_untouched(
    start_search, superuser_client, group, monkeypatch
):
    engine = start_search(_config())
    system = create_system(name="zebracorn", owner=group)
    jobs.drain_job()
    real_request = engine._client.request

    def failing_swap(method, path, **kwargs):
        if path == "/swap-indexes":
            raise meili_client.MeilisearchError("swap failed")
        return real_request(method, path, **kwargs)

    monkeypatch.setattr(engine._client, "request", failing_swap)

    jobs.rebuild_job()

    assert _last_error()[1] == indexer.REBUILD
    monkeypatch.setattr(engine._client, "request", real_request)
    assert _ids(superuser_client, "zebracorn") == [f"system:{system.pk}"]
