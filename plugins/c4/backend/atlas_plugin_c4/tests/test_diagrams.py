"""Diagram endpoint tests (`catalog-c4-diagrams`, `system-architecture-diagram`
specs).
"""

import pytest

pytestmark = pytest.mark.django_db

DIAGRAMS_URL = "/api/plugins/atlas.c4/diagrams"


def test_valid_target_returns_generated_svg(owner_client, system, monkeypatch):
    monkeypatch.setattr(
        "atlas_plugin_c4.c4.render", lambda *_args, **_kwargs: b"<svg />"
    )
    response = owner_client.get(
        f"{DIAGRAMS_URL}/system/{system.id}/", {"view": "context"}
    )
    assert response.status_code == 200
    assert response["Content-Type"] == "image/svg+xml"
    assert b"<svg" in response.content


def test_system_landscape_defaults_to_svg(owner_client, monkeypatch):
    captured = {}

    def render(payload, *, format):
        captured["payload"] = payload
        captured["format"] = format
        return b"<svg />"

    monkeypatch.setattr("atlas_plugin_c4.c4.render", render)

    response = owner_client.get(f"{DIAGRAMS_URL}/landscape/")

    assert response.status_code == 200
    assert response["Content-Type"] == "image/svg+xml"
    assert captured["format"] == "svg"
    assert captured["payload"]["title"] == "Atlas — System Landscape"


def test_system_landscape_supports_png_download(owner_client, monkeypatch):
    monkeypatch.setattr("atlas_plugin_c4.c4.render", lambda *_args, **_kwargs: b"png")

    response = owner_client.get(
        f"{DIAGRAMS_URL}/landscape/", {"format": "png", "download": "1"}
    )

    assert response.status_code == 200
    assert response["Content-Type"] == "image/png"
    assert response["Content-Disposition"].endswith('system-landscape.png"')


def test_diagram_request_applies_valid_rendering_settings(
    owner_client, system, monkeypatch
):
    captured = {}

    def render(payload, *, format):
        captured["payload"] = payload
        captured["format"] = format
        return b"<svg />"

    monkeypatch.setattr("atlas_plugin_c4.c4.render", render)

    response = owner_client.get(
        f"{DIAGRAMS_URL}/system/{system.id}/",
        {
            "view": "context",
            "layout": "LAYOUT_LEFT_RIGHT",
            "show_title": "false",
            "show_legend": "false",
            "show_person_sprite": "false",
            "show_stereotypes": "false",
        },
    )

    assert response.status_code == 200
    assert captured["payload"]["title"] is None
    assert captured["payload"]["render_options"] == {
        "layout": "LAYOUT_LEFT_RIGHT",
        "hide_stereotype": True,
        "hide_person_sprite": True,
        "tags": captured["payload"]["render_options"]["tags"],
    }


@pytest.mark.parametrize(
    "query",
    [
        {"layout": "LAYOUT_DIAGONAL"},
        {"show_legend": "not-a-boolean"},
    ],
)
def test_invalid_rendering_setting_returns_400(owner_client, system, query):
    response = owner_client.get(
        f"{DIAGRAMS_URL}/system/{system.id}/",
        {"view": "context"} | query,
    )

    assert response.status_code == 400


def test_component_png_download(owner_client, component, monkeypatch):
    monkeypatch.setattr("atlas_plugin_c4.c4.render", lambda *_args, **_kwargs: b"png")
    response = owner_client.get(
        f"{DIAGRAMS_URL}/component/{component.id}/",
        {"view": "component", "format": "png", "download": "1"},
    )
    assert response.status_code == 200
    assert response["Content-Type"] == "image/png"
    assert response["Content-Disposition"].endswith(f'component-{component.id}.png"')


def test_system_architecture_defaults_to_svg(owner_client, system, monkeypatch):
    captured = {}

    def render(payload, *, format):
        captured["payload"] = payload
        captured["format"] = format
        return b"<svg />"

    monkeypatch.setattr("atlas_plugin_c4.c4.render", render)

    response = owner_client.get(
        f"{DIAGRAMS_URL}/system/{system.id}/", {"view": "architecture"}
    )

    assert response.status_code == 200
    assert response["Content-Type"] == "image/svg+xml"
    assert captured["format"] == "svg"
    assert captured["payload"]["title"].endswith("System Architecture")


@pytest.mark.parametrize("format", ["svg", "png"])
def test_system_architecture_returns_requested_image_format(
    owner_client, system, monkeypatch, format
):
    monkeypatch.setattr("atlas_plugin_c4.c4.render", lambda *_args, **_kwargs: b"image")

    response = owner_client.get(
        f"{DIAGRAMS_URL}/system/{system.id}/",
        {"view": "architecture", "format": format, "download": "1"},
    )

    assert response.status_code == 200
    expected_content_type = "image/svg+xml" if format == "svg" else "image/png"
    assert response["Content-Type"] == expected_content_type
    assert response["Content-Disposition"].endswith(
        f'system-{system.id}-architecture.{format}"'
    )


def test_unknown_entity_id_returns_404(owner_client):
    response = owner_client.get(f"{DIAGRAMS_URL}/system/999999/", {"view": "context"})
    assert response.status_code == 404


def test_invalid_view_returns_400(owner_client, system):
    response = owner_client.get(
        f"{DIAGRAMS_URL}/system/{system.id}/", {"view": "bogus"}
    )
    assert response.status_code == 400


def test_invalid_kind_and_view_pair_returns_400(owner_client, component):
    response = owner_client.get(
        f"{DIAGRAMS_URL}/component/{component.id}/",
        {"view": "architecture"},
    )
    assert response.status_code == 400


def test_renderer_failure_is_controlled(owner_client, system, monkeypatch):
    from atlas_plugin_c4.c4 import DiagramRenderError

    def fail(*_args, **_kwargs):
        raise DiagramRenderError("private renderer details")

    monkeypatch.setattr("atlas_plugin_c4.c4.render", fail)
    response = owner_client.get(
        f"{DIAGRAMS_URL}/system/{system.id}/", {"view": "context"}
    )
    assert response.status_code == 500
    assert b"private renderer details" not in response.content


def test_unauthenticated_request_is_rejected(dmr_client, system):
    response = dmr_client.get(
        f"{DIAGRAMS_URL}/system/{system.id}/", {"view": "context"}
    )
    assert response.status_code == 401
