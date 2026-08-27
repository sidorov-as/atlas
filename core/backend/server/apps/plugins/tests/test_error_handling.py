"""`runtime-failure-isolation` spec: an internal failure in one plugin-owned
endpoint returns a clean degraded response and doesn't affect requests to
other endpoints.
"""

import pytest

pytestmark = pytest.mark.django_db

DIAGRAMS_URL = "/api/plugins/atlas.c4/diagrams/landscape/"


def test_unhandled_exception_in_a_plugin_endpoint_returns_a_clean_typed_500(
    owner_client,
    monkeypatch,
):
    def broken_render(*_args, **_kwargs):
        raise RuntimeError("boom: not a recognized DiagramRenderError")

    monkeypatch.setattr("atlas_plugin_c4.c4.render", broken_render)

    response = owner_client.get(DIAGRAMS_URL)

    assert response.status_code == 500
    body = response.json()
    assert "detail" in body
    assert isinstance(body["detail"], list)


def test_a_plugin_endpoint_failing_does_not_affect_a_later_request_to_core(
    owner_client,
    monkeypatch,
):
    def broken_render(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("atlas_plugin_c4.c4.render", broken_render)
    broken_response = owner_client.get(DIAGRAMS_URL)
    assert broken_response.status_code == 500

    healthy_response = owner_client.get("/api/systems/")
    assert healthy_response.status_code == 200
