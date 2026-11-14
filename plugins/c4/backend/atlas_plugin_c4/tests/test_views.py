"""Saved views: CRUD, rendering by id, and permissions (`c4-custom-view-diagram` spec)."""

from uuid import uuid4

import pytest
from atlas_plugin_api import get_architecture_relationship_model
from django.contrib.auth import get_user_model
from server.apps.catalog.models import AccountAccess
from server.apps.catalog.tests.factories import (
    create_actor,
    create_api,
    create_resource,
)

from atlas_plugin_c4.models import View

pytestmark = pytest.mark.django_db

VIEWS_URL = "/api/plugins/atlas.c4/views/"


def _url(view_id, suffix=""):
    return f"{VIEWS_URL}{view_id}/{suffix}"


@pytest.fixture
def captured(monkeypatch):
    calls = []

    def render(payload, *, format):
        calls.append((payload, format))
        return b"<svg />" if format == "svg" else b"PNG"

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


def _body(*entities, name="Billing", **overrides):
    return {
        "name": name,
        "description": "d",
        "settings": {
            "level": "components",
            "selection": "selected",
            "entities": [str(e.id if hasattr(e, "id") else e) for e in entities],
        },
        **overrides,
    }


def _create(client, *entities, **kwargs):
    return client.post(VIEWS_URL, data=_body(*entities, **kwargs), format="json")


def test_create_view(owner_client, pair):
    api, resource = pair
    response = _create(owner_client, api, resource)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Billing" and data["missingEntities"] == []
    assert data["settings"]["entities"] == [str(api.id), str(resource.id)]
    assert View.objects.get(pk=data["id"]).name == "Billing"


def test_name_is_required(owner_client, pair):
    assert _create(owner_client, pair[0], name="  ").status_code == 400
    assert View.objects.count() == 0


def test_duplicate_name_ignoring_case_is_a_name_error(owner_client, pair):
    assert _create(owner_client, pair[0]).status_code == 201
    response = _create(owner_client, pair[0], name="billing")
    assert response.status_code == 400
    assert response.json()["detail"][0]["loc"][-1] == "name"
    assert View.objects.count() == 1


@pytest.mark.parametrize(
    "settings",
    [
        {"entities": []},
        {"selection": "neighborhood", "depth": 0},
    ],
)
def test_invalid_settings_are_rejected(owner_client, pair, settings):
    body = _body(pair[0])
    body["settings"] |= settings
    response = owner_client.post(VIEWS_URL, data=body, format="json")
    assert response.status_code == 400
    assert View.objects.count() == 0


def test_unknown_entity_is_named_and_nothing_is_stored(owner_client):
    missing = uuid4()
    response = _create(owner_client, missing)
    assert response.status_code == 404
    assert response.json()["detail"][0]["entity"] == str(missing)
    assert View.objects.count() == 0


def test_mixed_levels_are_rejected(owner_client, system, pair):
    assert _create(owner_client, system, pair[0]).status_code == 400


def test_read_view(owner_client, pair):
    view_id = _create(owner_client, pair[0]).json()["id"]
    response = owner_client.get(_url(view_id))
    assert response.status_code == 200
    assert response.json()["name"] == "Billing"
    assert owner_client.get(_url(uuid4())).status_code == 404


def test_read_reports_missing_entities(owner_client, pair):
    api, resource = pair
    view_id = _create(owner_client, api, resource).json()["id"]
    resource_id = str(resource.id)
    resource.delete()
    response = owner_client.get(_url(view_id))
    assert response.status_code == 200
    assert response.json()["missingEntities"] == [resource_id]


def test_update_replaces_values_and_keeps_own_name(owner_client, pair):
    api, resource = pair
    created = _create(owner_client, api).json()
    response = owner_client.put(
        _url(created["id"]), data=_body(api, resource, name="Billing"), format="json"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["settings"]["entities"] == [str(api.id), str(resource.id)]
    assert data["updatedAt"] >= created["updatedAt"]


def test_update_rejects_name_of_another_view(owner_client, pair):
    _create(owner_client, pair[0], name="One")
    other = _create(owner_client, pair[0], name="Two").json()
    response = owner_client.put(
        _url(other["id"]), data=_body(pair[0], name="one"), format="json"
    )
    assert response.status_code == 400


def test_removed_entity_can_be_repaired(owner_client, pair, captured):
    api, resource = pair
    view_id = _create(owner_client, api, resource).json()["id"]
    resource_id = str(resource.id)
    resource.delete()
    response = owner_client.put(
        _url(view_id), data=_body(api, resource_id), format="json"
    )
    assert response.status_code == 404
    response = owner_client.put(_url(view_id), data=_body(api), format="json")
    assert response.status_code == 200
    assert owner_client.get(_url(view_id, "diagram/")).status_code == 200


def test_delete_removes_the_view_only(owner_client, pair):
    api, _ = pair
    view_id = _create(owner_client, api).json()["id"]
    assert owner_client.delete(_url(view_id)).status_code == 204
    assert not View.objects.exists()
    api.refresh_from_db()
    assert owner_client.delete(_url(view_id)).status_code == 404


def test_list_is_paginated_searchable_and_sortable(owner_client, pair):
    for name in ("Alpha", "Beta", "Gamma"):
        _create(owner_client, pair[0], name=name)
    page = owner_client.get(VIEWS_URL, {"page_size": 2}).json()
    assert page["count"] == 3 and page["numPages"] == 2
    assert [v["name"] for v in page["page"]["objectList"]] == ["Alpha", "Beta"]
    found = owner_client.get(VIEWS_URL, {"q": "amm"}).json()
    assert [v["name"] for v in found["page"]["objectList"]] == ["Gamma"]
    desc = owner_client.get(VIEWS_URL, {"sort": "-name"}).json()
    assert [v["name"] for v in desc["page"]["objectList"]] == ["Gamma", "Beta", "Alpha"]


def test_diagram_svg_png_and_download(owner_client, pair, captured):
    api, resource = pair
    view_id = _create(owner_client, api, resource).json()["id"]
    svg = owner_client.get(_url(view_id, "diagram/"))
    assert svg.status_code == 200 and svg["Content-Type"] == "image/svg+xml"
    assert len(captured[0][0]["relationships"]) == 1
    png = owner_client.get(_url(view_id, "diagram/"), {"format": "png", "download": 1})
    assert png["Content-Type"] == "image/png"
    assert png["Content-Disposition"].startswith("attachment")


def test_saved_view_diagram_renders_dark_and_stores_no_theme(
    owner_client, pair, captured
):
    api, resource = pair
    created = _create(owner_client, api, resource).json()

    light = owner_client.get(_url(created["id"], "diagram/"))
    dark = owner_client.get(
        _url(created["id"], "diagram/"),
        {"theme": "dark", "format": "png", "download": 1},
    )

    assert light.status_code == dark.status_code == 200
    assert "atlas_theme" not in captured[0][0]
    assert (captured[1][0]["atlas_theme"], captured[1][1]) == ("dark", "png")
    assert "theme" not in created["settings"]
    assert "theme" not in owner_client.get(_url(created["id"])).json()["settings"]


def test_saved_view_diagram_rejects_an_invalid_theme(owner_client, pair, captured):
    api, resource = pair
    view_id = _create(owner_client, api, resource).json()["id"]

    response = owner_client.get(_url(view_id, "diagram/"), {"theme": "sepia"})

    assert response.status_code == 400
    assert captured == []


def test_diagram_unknown_view_is_404(owner_client, captured):
    assert owner_client.get(_url(uuid4(), "diagram/")).status_code == 404
    assert captured == []


def test_diagram_with_removed_entity_names_it(owner_client, pair, captured):
    api, resource = pair
    view_id = _create(owner_client, api, resource).json()["id"]
    resource_id = str(resource.id)
    resource.delete()
    response = owner_client.get(_url(view_id, "diagram/"))
    assert response.status_code == 404
    assert response.json()["detail"][0]["entity"] == resource_id
    assert captured == []


def test_non_owner_can_create_edit_and_delete(dmr_client, pair, group, owner_client):
    api, _ = pair
    view_id = _create(owner_client, api).json()["id"]
    user = get_user_model().objects.create_user(username="other", password="pw12345!")
    create_actor(name="other", account=user)
    dmr_client.force_login(user)
    assert _create(dmr_client, api, name="Mine").status_code == 201
    assert (
        dmr_client.put(
            _url(view_id), data=_body(api, name="Edited"), format="json"
        ).status_code
        == 200
    )
    assert dmr_client.delete(_url(view_id)).status_code == 204


def test_read_only_user_cannot_write_but_can_read(owner_client, owner_account, pair):
    api, _ = pair
    view_id = _create(owner_client, api).json()["id"]
    AccountAccess.objects.create(account=owner_account, read_only=True)
    assert _create(owner_client, api, name="New").status_code == 403
    put = owner_client.put(_url(view_id), data=_body(api), format="json")
    assert put.status_code == 403
    assert owner_client.delete(_url(view_id)).status_code == 403
    assert View.objects.count() == 1
    assert owner_client.get(_url(view_id)).status_code == 200


def test_unauthenticated_requests_are_rejected(dmr_client, pair, captured):
    api, _ = pair
    view = View.objects.create(name="v", settings={})
    assert dmr_client.get(VIEWS_URL).status_code == 401
    assert _create(dmr_client, api).status_code == 401
    assert dmr_client.get(_url(view.id)).status_code == 401
    assert dmr_client.delete(_url(view.id)).status_code == 401
    assert dmr_client.get(_url(view.id, "diagram/")).status_code == 401
    assert captured == []


class _Deny:
    def check(self, *_args):
        return False


def test_diagram_read_permission_is_required(owner_client, pair, captured, monkeypatch):
    view_id = _create(owner_client, pair[0]).json()["id"]
    monkeypatch.setattr("atlas_plugin_c4.permissions.get_policy_evaluator", _Deny)
    assert owner_client.get(VIEWS_URL).status_code == 403
    assert owner_client.get(_url(view_id)).status_code == 403
    assert owner_client.get(_url(view_id, "diagram/")).status_code == 403
    assert captured == []


def test_openapi_documents_the_view_endpoints():
    from dmr.openapi import OpenAPIConfig, build_schema

    from atlas_plugin_c4.api.urls import router

    paths = build_schema(
        router, config=OpenAPIConfig(title="t", version="1")
    ).convert()["paths"]
    base = "/api/plugins/atlas.c4/views/"
    assert {"get", "post"} <= set(paths[base])
    assert {"get", "put", "delete"} <= set(paths[base + "{id}/"])
    assert "get" in paths[base + "{id}/diagram/"]
