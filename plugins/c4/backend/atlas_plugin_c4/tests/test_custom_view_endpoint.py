"""`diagrams/custom/` (POST preview) and `custom-view/actor-kinds/` endpoints."""

from uuid import uuid4

import pytest
from atlas_plugin_api import get_architecture_relationship_model
from server.apps.catalog.tests.factories import create_api, create_resource

pytestmark = pytest.mark.django_db

CUSTOM_URL = "/api/plugins/atlas.c4/diagrams/custom/"
ACTOR_KINDS_URL = "/api/plugins/atlas.c4/custom-view/actor-kinds/"


class _Deny:
    def check(self, *_args):
        return False


@pytest.fixture
def captured(monkeypatch):
    calls = []

    def render(payload, *, format):
        calls.append((payload, format))
        return b"<svg />"

    monkeypatch.setattr("atlas_plugin_c4.c4.render", render)
    return calls


@pytest.fixture
def pair(group, system):
    api = create_api(name="api", owner=group, system=system)
    resource = create_resource(name="db", owner=group, system=system)
    get_architecture_relationship_model().objects.create(
        source=api, target=resource, label="Reads"
    )
    return api, resource


def _post(client, body, query=""):
    return client.post(CUSTOM_URL + query, data=body, format="json")


def _body(*entities, **overrides):
    return {
        "level": "components",
        "selection": "selected",
        "entities": [str(e) for e in entities],
        **overrides,
    }


def test_preview_renders_svg(owner_client, pair, captured):
    api, resource = pair
    response = _post(owner_client, _body(api.id, resource.id))
    assert response.status_code == 200
    assert response["Content-Type"] == "image/svg+xml"
    payload, fmt = captured[0]
    assert fmt == "svg"
    assert len(payload["relationships"]) == 1


def test_png_download(owner_client, pair, captured):
    api, _ = pair
    response = _post(
        owner_client,
        _body(api.id, selection="neighborhood", depth="all"),
        "?format=png&download=1",
    )
    assert response.status_code == 200
    assert response["Content-Type"] == "image/png"
    assert response["Content-Disposition"].endswith('custom-view.png"')


def test_rendering_options_come_from_the_query(owner_client, pair, captured):
    api, _ = pair
    response = _post(owner_client, _body(api.id), "?show_legend=false")
    assert response.status_code == 200
    assert captured


def test_settings_in_the_query_string_are_ignored(owner_client, pair, captured):
    api, resource = pair
    response = _post(
        owner_client,
        _body(api.id),
        f"?level=systems&entity={resource.id}&selection=neighborhood",
    )
    assert response.status_code == 200
    payload, _ = captured[0]
    assert payload["relationships"] == []


def test_preview_does_not_accept_get(owner_client, pair, captured):
    assert owner_client.get(CUSTOM_URL).status_code == 405
    assert captured == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"entities": []},
        {"entities": ["not-a-uuid"]},
        {"level": "containers"},
        {"selection": "neighborhood", "depth": 0},
        {"selection": "neighborhood", "direction": "up"},
    ],
)
def test_invalid_settings_return_400(owner_client, pair, captured, overrides):
    api, _ = pair
    response = _post(owner_client, _body(api.id) | overrides)
    assert response.status_code == 400
    assert captured == []


def test_missing_body_returns_400(owner_client, captured):
    assert _post(owner_client, {}).status_code == 400
    assert captured == []


def test_unknown_entity_returns_404_naming_it(owner_client, captured):
    missing = uuid4()
    response = _post(owner_client, _body(missing))
    assert response.status_code == 404
    detail = response.json()["detail"][0]
    assert (detail["type"], detail["entity"]) == ("unknown_entity", str(missing))
    assert captured == []


def test_mixed_levels_return_400(owner_client, system, pair, captured):
    api, _ = pair
    response = _post(owner_client, _body(system.id, api.id))
    assert response.status_code == 400
    assert response.json()["detail"][0]["type"] == "mixed_level_selection"


def test_node_limit_returns_422_without_rendering(
    owner_client, pair, captured, monkeypatch
):
    from atlas_plugin_c4 import c4

    monkeypatch.setattr(
        c4, "plugin_config", lambda: c4.C4PluginConfig.model_validate({"maxNodes": 1})
    )
    api, resource = pair
    response = _post(owner_client, _body(api.id, resource.id))
    assert response.status_code == 422
    detail = response.json()["detail"][0]
    assert (detail["type"], detail["limit"], detail["count"]) == (
        "node_limit_exceeded",
        1,
        2,
    )
    assert captured == []


def test_render_failure_returns_500(owner_client, pair, monkeypatch):
    from atlas_plugin_c4 import c4

    def fail(*_args, **_kwargs):
        raise c4.DiagramRenderError("boom")

    monkeypatch.setattr(c4, "render", fail)
    api, _ = pair
    assert _post(owner_client, _body(api.id)).status_code == 500


def test_unauthenticated_requests_are_rejected(dmr_client, pair, captured):
    assert _post(dmr_client, _body(pair[0].id)).status_code == 401
    assert dmr_client.get(ACTOR_KINDS_URL).status_code == 401
    assert captured == []


def test_missing_permission_is_rejected(owner_client, pair, captured, monkeypatch):
    monkeypatch.setattr("atlas_plugin_c4.permissions.get_policy_evaluator", _Deny)
    assert _post(owner_client, _body(pair[0].id)).status_code == 403
    assert owner_client.get(ACTOR_KINDS_URL).status_code == 403
    assert captured == []


def test_actor_kinds_lists_capability_declaring_kinds_only(owner_client):
    response = owner_client.get(ACTOR_KINDS_URL)
    assert response.status_code == 200
    kinds = {item["kind"]: item["label"] for item in response.json()["items"]}
    assert "group" in kinds
    assert "system" not in kinds and "component" not in kinds
    assert all(kinds.values())


def test_actor_kinds_includes_newly_registered_kind(owner_client, monkeypatch):
    from atlas_plugin_api import registry

    monkeypatch.setattr(
        registry,
        "kind_ids_with_capability",
        lambda capability: ["bot", "group"],
    )
    kinds = {i["kind"] for i in owner_client.get(ACTOR_KINDS_URL).json()["items"]}
    assert kinds == {"bot", "group"}


def test_openapi_documents_the_new_endpoints():
    from dmr.openapi import OpenAPIConfig, build_schema

    from atlas_plugin_c4.api.urls import router

    schema = build_schema(
        router, config=OpenAPIConfig(title="t", version="1")
    ).convert()
    paths = schema["paths"]
    custom_path = paths["/api/plugins/atlas.c4/diagrams/custom/"]
    assert "get" not in custom_path
    custom = custom_path["post"]
    assert "requestBody" in custom
    names = {p["name"] for p in custom.get("parameters", [])}
    assert not {"level", "selection", "entity", "depth", "entity_type"} & names
    assert {"400", "404", "422"} <= set(custom["responses"])
    assert "/api/plugins/atlas.c4/custom-view/actor-kinds/" in paths
