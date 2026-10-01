"""`describe_kinds` reports the writable kinds' spec shapes, derived from
the registered handlers (`mcp-kind-introspection` spec)."""

import atlas_plugin_api.pat as pat_module
import pytest
from atlas_plugin_api import registry
from atlas_plugin_api.pat import ResolvedPersonalAccessToken, bind_pat_validator

pytestmark = pytest.mark.django_db

_KINDS = "/api/plugins/atlas.mcp/kinds/"


def _get(dmr_client, header, **query):
    return dmr_client.get(_KINDS, data=query, **header)


def _by_kind(response) -> dict:
    return {entry["kind"]: entry for entry in response.json()}


def _enum_values(entry_schema: dict, field: str) -> set[str]:
    prop = entry_schema["properties"][field]
    if "$ref" in prop:
        prop = entry_schema["$defs"][prop["$ref"].rsplit("/", 1)[-1]]
    return set(prop["enum"])


def test_component_enums_and_required_fields_are_reported(dmr_client, pat_auth_header):
    response = _get(dmr_client, pat_auth_header)

    assert response.status_code == 200
    component = _by_kind(response)["component"]["createSpec"]
    assert _enum_values(component, "type") == {
        "service",
        "website",
        "library",
        "worker",
    }
    assert _enum_values(component, "lifecycle") == {
        "experimental",
        "production",
        "deprecated",
    }
    assert {"owner", "system"} <= set(component["required"])


def test_resource_is_reported(dmr_client, pat_auth_header):
    kinds = _by_kind(_get(dmr_client, pat_auth_header))

    assert "resource" in kinds
    assert "system" in kinds


def test_api_fields_are_reported_when_apis_is_installed(dmr_client, pat_auth_header):
    api = _by_kind(_get(dmr_client, pat_auth_header))["api"]["createSpec"]

    assert _enum_values(api, "specSource") == {"none", "inline", "url"}
    assert api["properties"]["specContent"]["maxLength"] > 0


def test_api_is_absent_when_the_kind_is_not_registered(
    dmr_client, pat_auth_header, monkeypatch
):
    monkeypatch.delitem(registry._handlers, "api")

    kinds = _by_kind(_get(dmr_client, pat_auth_header))

    assert "api" not in kinds
    assert "component" in kinds


def test_only_writable_kinds_are_listed(dmr_client, pat_auth_header):
    kinds = _by_kind(_get(dmr_client, pat_auth_header))

    assert "group" not in kinds
    assert "actor" not in kinds


def test_no_schema_lists_relationships(dmr_client, pat_auth_header):
    for entry in _get(dmr_client, pat_auth_header).json():
        for key in ("createSpec", "patchSpec"):
            assert "relationships" not in entry[key]["properties"]
            assert "relationships" not in entry[key].get("required", [])


def test_patch_schema_has_no_required_fields(dmr_client, pat_auth_header):
    component = _by_kind(_get(dmr_client, pat_auth_header))["component"]

    assert not component["patchSpec"].get("required")


def test_kind_filter_returns_one_kind(dmr_client, pat_auth_header):
    response = _get(dmr_client, pat_auth_header, kind="component")

    assert response.status_code == 200
    assert [entry["kind"] for entry in response.json()] == ["component"]


@pytest.mark.parametrize("kind", ["group", "nonsense"])
def test_kind_filter_rejects_unknown_or_non_writable_kinds(
    dmr_client, pat_auth_header, kind
):
    response = _get(dmr_client, pat_auth_header, kind=kind)

    assert response.status_code == 400
    assert kind in str(response.json())


def test_unauthenticated_request_is_rejected(dmr_client):
    response = dmr_client.get(_KINDS)

    assert response.status_code == 401
    assert "createSpec" not in response.content.decode()


def test_catalog_read_scope_is_required(dmr_client, owner_account):
    previous = pat_module._pat_validator
    bind_pat_validator(
        lambda raw: (
            ResolvedPersonalAccessToken(
                user=owner_account, scopes=frozenset({"flows:read"})
            )
            if raw == "atlaspat_no-catalog-scope"
            else None
        )
    )
    try:
        response = _get(
            dmr_client,
            {"HTTP_AUTHORIZATION": "Bearer atlaspat_no-catalog-scope"},
        )
    finally:
        pat_module._pat_validator = previous

    assert response.status_code == 403
