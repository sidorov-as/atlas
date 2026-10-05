"""Entity CRUD tests.

Covers creation, the ownership permission (member/non-member/superuser),
YAML-managed read-only enforcement, unrestricted non-owner read access, and
that Group/User creation via the API is rejected.
"""

import pytest
from atlas_plugin_ingestion.claims import claim_entity

from server.apps.catalog.models import (
    KIND_COMPONENT,
    KIND_GROUP,
    KIND_SYSTEM,
    CatalogEntity,
)
from server.apps.catalog.tests.factories import (
    create_component,
    create_resource,
    create_system,
)

pytestmark = pytest.mark.django_db


def test_member_of_owner_group_creates_system(owner_client, group):
    response = owner_client.post(
        "/api/systems/",
        {
            "metadata": {"name": "new-system"},
            "spec": {"owner": "group:platform"},
        },
    )
    assert response.status_code == 201
    assert CatalogEntity.objects.filter(
        kind=KIND_SYSTEM, name="new-system"
    ).exists()

    listed = owner_client.get("/api/systems/")
    assert listed.status_code == 200
    assert any(
        item["metadata"]["name"] == "new-system"
        for item in listed.json()["page"]["objectList"]
    )


def test_documentation_defaults_and_round_trips_via_create_patch_and_read(
    owner_client, group
):
    response = owner_client.post(
        "/api/systems/",
        {
            "metadata": {"name": "documented-system"},
            "spec": {"owner": "group:platform"},
        },
    )
    assert response.status_code == 201
    system_id = response.json()["id"]
    assert response.json()["metadata"]["documentation"] == ""

    updated = owner_client.patch(
        f"/api/systems/{system_id}/",
        {
            "metadata": {
                "documentation": "## Runbook\n\nFollow the [guide](/guide)."
            }
        },
    )
    assert updated.status_code == 200
    assert updated.json()["metadata"]["documentation"].startswith("## Runbook")

    read = owner_client.get(f"/api/systems/{system_id}/")
    assert (
        read.json()["metadata"]["documentation"]
        == "## Runbook\n\nFollow the [guide](/guide)."
    )


def test_system_document_links_are_described_searchable_paginated_and_read_only(
    owner_client, system
):
    system.links = [
        {
            "url": "https://docs.example.test/runbook",
            "title": "Runbook",
            "description": "Checkout dashboard guide",
            "type": "runbook",
        },
        {
            "url": "https://docs.example.test/wiki",
            "title": "Wiki",
            "type": "wiki",
        },
        {
            "url": "https://docs.example.test/adr",
            "title": "Architecture",
            "description": "Dashboard decisions",
            "type": "adr",
        },
    ]
    system.save(update_fields=["links"])

    detail = owner_client.get(f"/api/systems/{system.id}/")
    assert detail.json()["metadata"]["links"][1]["description"] == ""

    response = owner_client.get(
        f"/api/systems/{system.id}/docs/", {"q": "DASHBOARD", "page_size": 1}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    assert body["numPages"] == 2
    assert body["page"]["objectList"][0]["url"].endswith("/runbook")

    second_page = owner_client.get(
        f"/api/systems/{system.id}/docs/",
        {"q": "dashboard", "page": 2, "page_size": 1},
    )
    assert second_page.json()["page"]["objectList"][0]["url"].endswith("/adr")
    assert (
        owner_client.post(f"/api/systems/{system.id}/docs/", {}).status_code
        == 405
    )


def test_non_member_cannot_create_system_for_group(other_client, group):
    response = other_client.post(
        "/api/systems/",
        {
            "metadata": {"name": "blocked-system"},
            "spec": {"owner": "group:platform"},
        },
    )
    assert response.status_code == 403
    assert not CatalogEntity.objects.filter(
        kind=KIND_SYSTEM, name="blocked-system"
    ).exists()


def test_non_member_cannot_edit_manual_system(other_client, system):
    response = other_client.patch(
        f"/api/systems/{system.id}/", {"metadata": {"title": "Hijacked"}}
    )
    assert response.status_code == 403
    system.refresh_from_db()
    assert system.title == ""


def test_yaml_managed_system_cannot_be_patched_by_owner_member(
    owner_client, group
):
    from atlas_plugin_ingestion.models import RegisteredRepository

    repo = RegisteredRepository.objects.create(
        source_id="test-source", path="org/repo"
    )
    managed = create_system(
        name="managed-system",
        owner=group,
        source_kind="yaml",
    )
    claim_entity(managed, repo)

    patch_response = owner_client.patch(
        f"/api/systems/{managed.id}/", {"metadata": {"title": "Edited"}}
    )
    assert patch_response.status_code == 403
    assert CatalogEntity.objects.filter(pk=managed.id).exists()


def test_entity_created_by_ingestion_rejects_manual_writes(owner_client, group):
    """End to end: the entity is written by ingestion itself (not a test
    factory), then the owner's manual PATCH is rejected and the
    entity reports the claiming repository."""
    from atlas_plugin_ingestion.models import RegisteredRepository
    from atlas_plugin_ingestion.pipeline import _ingest_manifest

    repo = RegisteredRepository.objects.create(
        source_id="test-source", path="org/repo"
    )
    manifest = (
        b"apiVersion: atlas/v1alpha1\nkind: System\n"
        b"metadata:\n  name: ingested-system\n"
        b"spec:\n  owner: group:platform\n"
    )
    _ingest_manifest(repo, "catalog-info.yaml", manifest)
    managed = CatalogEntity.objects.get(
        kind=KIND_SYSTEM, name="ingested-system"
    )

    detail = owner_client.get(f"/api/systems/{managed.id}/")
    assert detail.status_code == 200
    assert detail.json()["ingestedFrom"] == "test-source/org/repo"

    patch_response = owner_client.patch(
        f"/api/systems/{managed.id}/", {"metadata": {"title": "Edited"}}
    )
    assert patch_response.status_code == 403
    managed.refresh_from_db()
    assert managed.title == ""


def test_superuser_can_edit_manual_entity_regardless_of_membership(
    superuser_client, other_group
):
    system = create_system(name="other-team-system", owner=other_group)

    response = superuser_client.patch(
        f"/api/systems/{system.id}/",
        {"metadata": {"title": "Updated by admin"}},
    )
    assert response.status_code == 200
    system.refresh_from_db()
    assert system.title == "Updated by admin"


def test_non_owner_can_read_entity_they_do_not_own(other_client, system):
    response = other_client.get(f"/api/systems/{system.id}/")
    assert response.status_code == 200
    assert response.json()["metadata"]["name"] == system.name


def test_system_response_includes_owner_id(owner_client, system, group):
    response = owner_client.get(f"/api/systems/{system.id}/")
    assert response.status_code == 200
    assert response.json()["spec"]["ownerId"] == str(group.id)


def test_component_response_includes_owner_and_system_id(
    owner_client, component, group, system
):
    response = owner_client.get(f"/api/components/{component.id}/")
    assert response.status_code == 200
    spec = response.json()["spec"]
    assert spec["ownerId"] == str(group.id)
    assert spec["systemId"] == str(system.id)


def test_system_response_includes_its_declared_capabilities(
    owner_client, system
):
    response = owner_client.get(f"/api/systems/{system.id}/")
    assert response.status_code == 200
    assert response.json()["capabilities"] == ["architecture.subject.v1"]


def test_component_response_includes_its_declared_capabilities(
    owner_client, component
):
    response = owner_client.get(f"/api/components/{component.id}/")
    assert response.status_code == 200
    assert response.json()["capabilities"] == ["architecture.subject.v1"]


def test_resource_response_includes_its_declared_capabilities(
    owner_client, resource
):
    response = owner_client.get(f"/api/resources/{resource.id}/")
    assert response.status_code == 200
    assert response.json()["capabilities"] == ["schema.host.v1"]


def test_group_response_includes_its_declared_capabilities(owner_client, group):
    response = owner_client.get(f"/api/groups/{group.id}/")
    assert response.status_code == 200
    assert response.json()["capabilities"] == ["architecture.actor.v1"]


def test_resource_response_includes_owner_and_system_id(
    owner_client, resource, group
):
    response = owner_client.get(f"/api/resources/{resource.id}/")
    assert response.status_code == 200
    spec = response.json()["spec"]
    assert spec["ownerId"] == str(group.id)
    assert spec["systemId"] is None


def test_resource_with_system_response_includes_system_id(
    owner_client, group, system
):
    with_system = create_resource(
        name="cache", owner=group, type="cache", system=system
    )

    response = owner_client.get(f"/api/resources/{with_system.id}/")
    assert response.status_code == 200
    assert response.json()["spec"]["systemId"] == str(system.id)


def test_api_response_includes_owner_and_system_id(
    owner_client, api, group, system
):
    response = owner_client.get(f"/api/apis/{api.id}/")
    assert response.status_code == 200
    spec = response.json()["spec"]
    assert spec["ownerId"] == str(group.id)
    assert spec["systemId"] == str(system.id)


def test_component_created_with_valid_references(
    owner_client, group, system, resource, api
):
    response = owner_client.post(
        "/api/components/",
        {
            "metadata": {"name": "checkout-service"},
            "spec": {
                "type": "service",
                "lifecycle": "production",
                "owner": "group:platform",
                "system": "system:user-management",
                "dependsOn": ["resource:primary-db"],
                "providesApis": ["api:user-api"],
            },
        },
    )
    assert response.status_code == 201


def test_component_creation_rejects_dangling_reference(
    owner_client, group, system
):
    response = owner_client.post(
        "/api/components/",
        {
            "metadata": {"name": "broken-service"},
            "spec": {
                "type": "service",
                "lifecycle": "production",
                "owner": "group:platform",
                "system": "system:user-management",
                "dependsOn": ["resource:does-not-exist"],
            },
        },
    )
    assert response.status_code == 400
    assert not CatalogEntity.objects.filter(
        kind=KIND_COMPONENT, name="broken-service"
    ).exists()


def test_creating_group_via_api_is_rejected(owner_client):
    response = owner_client.post(
        "/api/groups/",
        {"metadata": {"name": "shadow-team"}, "spec": {"type": "team"}},
    )
    assert response.status_code == 405
    assert not CatalogEntity.objects.filter(
        kind=KIND_GROUP, name="shadow-team"
    ).exists()


def test_creating_user_via_api_is_rejected(owner_client):
    response = owner_client.post(
        "/api/users/", {"metadata": {"name": "shadow-user"}}
    )
    assert response.status_code == 405


def test_list_filters_by_owner(owner_client, group, other_group):
    create_system(name="owned-by-platform", owner=group)
    create_system(name="owned-by-other", owner=other_group)

    response = owner_client.get("/api/systems/", {"owner": "group:platform"})
    assert response.status_code == 200
    names = {
        item["metadata"]["name"]
        for item in response.json()["page"]["objectList"]
    }
    assert names == {"owned-by-platform"}


def test_list_search_matches_name_description_or_documentation(
    owner_client, group
):
    create_system(
        name="user-directory", owner=group, description="Handles users"
    )
    create_system(name="billing", owner=group, description="Handles invoices")
    create_system(
        name="identity",
        owner=group,
        documentation="How to reset a user password",
    )

    response = owner_client.get("/api/systems/", {"q": "user"})
    assert response.status_code == 200
    names = {
        item["metadata"]["name"]
        for item in response.json()["page"]["objectList"]
    }
    assert names == {"user-directory", "identity"}


def test_list_filters_by_any_tag_and_paginates(owner_client, group):
    create_system(name="payments", owner=group, tags=["payments"])
    create_system(name="internal", owner=group, tags=["internal"])
    create_system(name="both", owner=group, tags=["payments", "internal"])
    create_system(name="public", owner=group, tags=["public"])

    filtered = owner_client.get("/api/systems/?tags=payments&tags=internal")
    assert filtered.status_code == 200
    assert {
        item["metadata"]["name"]
        for item in filtered.json()["page"]["objectList"]
    } == {
        "payments",
        "internal",
        "both",
    }

    paginated = owner_client.get("/api/systems/", {"page": 2, "page_size": 2})
    assert paginated.status_code == 200
    payload = paginated.json()
    assert payload["count"] == 4
    assert payload["numPages"] == 2
    assert payload["perPage"] == 2
    assert payload["page"]["number"] == 2
    assert len(payload["page"]["objectList"]) == 2


def test_list_page_size_has_upper_bound(owner_client):
    response = owner_client.get("/api/systems/", {"page_size": 101})
    assert response.status_code == 400


def test_component_list_filters_by_system(owner_client, group):
    first = create_system(name="first", owner=group)
    second = create_system(name="second", owner=group)
    create_component(name="in-first", owner=group, system=first)
    create_component(name="in-second", owner=group, system=second)

    response = owner_client.get("/api/components/", {"system": "system:first"})
    assert response.status_code == 200
    assert [
        item["metadata"]["name"]
        for item in response.json()["page"]["objectList"]
    ] == ["in-first"]
