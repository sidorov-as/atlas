"""Adopt endpoint tests."""

import pytest
from atlas_plugin_ingestion.models import RegisteredRepository
from atlas_plugin_ingestion.upsert import upsert_entity
from atlas_plugin_ingestion.validation import validate_manifest_document

from server.apps.catalog.models import KIND_SYSTEM, CatalogEntity
from server.apps.catalog.tests.factories import create_system

pytestmark = pytest.mark.django_db


@pytest.fixture
def repo(db):
    return RegisteredRepository.objects.create(
        source_id="test-source", path="org/repo"
    )


def test_owner_adopts_a_manual_entity(owner_client, group, repo):
    system = create_system(name="user-management", owner=group)

    response = owner_client.post(
        f"/api/systems/{system.id}/adopt/", {"repository": str(repo)}
    )

    assert response.status_code == 200
    system.refresh_from_db()
    assert system.source_kind == CatalogEntity.SOURCE_YAML
    assert system.ingested_from_id == repo.id


def test_adopt_does_not_touch_other_fields(owner_client, group, repo):
    system = create_system(
        name="user-management", owner=group, title="Original Title"
    )

    owner_client.post(
        f"/api/systems/{system.id}/adopt/", {"repository": str(repo)}
    )

    system.refresh_from_db()
    assert system.title == "Original Title"


def test_non_owner_cannot_adopt(other_client, group, repo):
    system = create_system(name="user-management", owner=group)

    response = other_client.post(
        f"/api/systems/{system.id}/adopt/", {"repository": str(repo)}
    )

    assert response.status_code == 403
    system.refresh_from_db()
    assert system.source_kind == CatalogEntity.SOURCE_MANUAL


def test_adopting_an_already_yaml_managed_entity_is_rejected(
    owner_client, group, repo
):
    system = create_system(
        name="user-management",
        owner=group,
        source_kind="yaml",
        ingested_from=repo,
    )

    other_repo = RegisteredRepository.objects.create(
        source_id="test-source", path="org/other-repo"
    )
    response = owner_client.post(
        f"/api/systems/{system.id}/adopt/", {"repository": str(other_repo)}
    )

    assert response.status_code == 403
    system.refresh_from_db()
    assert system.ingested_from_id == repo.id


def test_adopted_entity_is_overwritten_on_next_ingestion(
    owner_client, group, repo
):
    system = create_system(
        name="user-management", owner=group, title="Hand Written"
    )

    owner_client.post(
        f"/api/systems/{system.id}/adopt/", {"repository": str(repo)}
    )

    doc = validate_manifest_document(
        {
            "apiVersion": "atlas/v1alpha1",
            "kind": "System",
            "metadata": {"name": "user-management", "title": "From Git"},
            "spec": {"owner": "group:platform"},
        },
    )
    upsert_entity(doc, repo)

    system.refresh_from_db()
    assert system.title == "From Git"
    assert (
        CatalogEntity.objects.filter(
            kind=KIND_SYSTEM, name="user-management"
        ).count()
        == 1
    )
