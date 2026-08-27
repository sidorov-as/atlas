"""`runtime-failure-isolation` spec: "A health/diagnostics endpoint SHALL
report each installed plugin's status, distinguishing healthy from
degraded".
"""

import pytest

from server.apps.plugins.health import (
    mark_degraded,
    plugin_health,
    reset_degraded,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _reset_degraded_plugins():
    reset_degraded()
    yield
    reset_degraded()


def test_every_selected_plugin_starts_active():
    statuses = {status.id: status.status for status in plugin_health()}
    assert statuses["atlas.c4"] == "active"
    assert statuses["atlas.database-schema"] == "active"


def test_marking_a_plugin_degraded_is_reflected_in_its_status():
    mark_degraded("atlas.c4", "boom")
    statuses = {status.id: status.status for status in plugin_health()}
    assert statuses["atlas.c4"] == "degraded"
    assert statuses["atlas.database-schema"] == "active"


def test_healthz_plugins_endpoint_reports_every_plugin(client):
    response = client.get("/healthz/plugins/")
    assert response.status_code == 200
    body = response.json()
    plugin_ids = {plugin["id"] for plugin in body["plugins"]}
    assert "atlas.c4" in plugin_ids
    for plugin in body["plugins"]:
        assert plugin["status"] == "active"


def test_healthz_plugins_endpoint_reports_a_degraded_plugin_with_503(client):
    mark_degraded("atlas.apis", "boom")

    response = client.get("/healthz/plugins/")

    assert response.status_code == 503
    body = response.json()
    statuses = {p["id"]: p["status"] for p in body["plugins"]}
    assert statuses["atlas.apis"] == "degraded"
    assert statuses["atlas.c4"] == "active"


def test_an_unhandled_plugin_exception_marks_that_plugin_degraded(
    owner_client,
    monkeypatch,
):
    def broken_render(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("atlas_plugin_c4.c4.render", broken_render)
    owner_client.get("/api/plugins/atlas.c4/diagrams/landscape/")

    response = owner_client.get("/healthz/plugins/")
    statuses = {p["id"]: p["status"] for p in response.json()["plugins"]}
    assert statuses["atlas.c4"] == "degraded"
    assert statuses["atlas.database-schema"] == "active"
