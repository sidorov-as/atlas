"""RegisteredRepository deletion/unregistration (the block applies regardless of an entity's
`active`/`removed` status, and is only cleared by Remove-then-Purge).

`RegisteredRepositoryAdmin` has no custom delete logic — the block comes from
`CatalogEntity.ingested_from` being `on_delete=PROTECT`, and the "succeeds"
half is `ConflictRecord.repository` being `on_delete=SET_NULL` instead. These
tests exercise that at the ORM level, which is what actually enforces it
regardless of the interface (Django admin) sitting in front of it.
"""

import pytest
from atlas_plugin_api import SOURCE_YAML, get_catalog_entity_model, get_entity_service
from django.contrib.auth import get_user_model
from django.db.models import ProtectedError
from server.apps.catalog.tests.factories import create_system

from atlas_plugin_ingestion.models import ConflictRecord, RegisteredRepository
from atlas_plugin_ingestion.upsert import ClaimRejected, upsert_entity
from atlas_plugin_ingestion.validation import validate_manifest_document

pytestmark = pytest.mark.django_db


def _superuser():
    return get_user_model().objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="password123",
    )


def _system_doc(name: str):
    return validate_manifest_document(
        {
            "apiVersion": "atlas/v1alpha1",
            "kind": "System",
            "metadata": {"name": name},
            "spec": {"owner": "group:platform"},
        },
    )


def test_unregistration_rejected_while_an_entity_is_claimed(repo, group):
    upsert_entity(_system_doc("user-management"), repo)

    with pytest.raises(ProtectedError):
        repo.delete()

    assert RegisteredRepository.objects.filter(pk=repo.pk).exists()


def test_unregistration_succeeds_once_all_claimed_entities_are_deleted(repo, group):
    system = upsert_entity(_system_doc("user-management"), repo)
    system.delete()

    repo.delete()

    assert not RegisteredRepository.objects.filter(pk=repo.pk).exists()


def test_unregistration_still_blocked_while_a_claimed_entity_is_removed_but_not_purged(
    repo, group
):
    system = upsert_entity(_system_doc("user-management"), repo)
    get_entity_service().remove(entity_id=system.id, actor=None, source=SOURCE_YAML)

    with pytest.raises(ProtectedError):
        repo.delete()

    assert RegisteredRepository.objects.filter(pk=repo.pk).exists()
    system.refresh_from_db()
    assert system.status == get_catalog_entity_model().STATUS_REMOVED


def test_unregistration_succeeds_once_the_claimed_entity_is_removed_then_purged(
    repo, group
):
    system = upsert_entity(_system_doc("user-management"), repo)
    get_entity_service().remove(entity_id=system.id, actor=None, source=SOURCE_YAML)
    get_entity_service().purge(entity_id=system.id, actor=_superuser())

    repo.delete()

    assert not RegisteredRepository.objects.filter(pk=repo.pk).exists()
    assert not get_catalog_entity_model().objects.filter(pk=system.id).exists()


def test_repository_with_only_historical_conflicts_can_be_deleted(repo, group):
    manual = create_system(name="user-management", owner=group)
    with pytest.raises(ClaimRejected):
        upsert_entity(_system_doc("user-management"), repo)

    manual.delete()
    upsert_entity(
        _system_doc("user-management"), repo
    )  # resolves the conflict, but repo now claims the entity

    conflict = ConflictRecord.objects.get(kind="system", name="user-management")
    assert conflict.is_active is False

    system = get_catalog_entity_model().objects.get(
        kind="system", name="user-management"
    )
    system.delete()  # repo claims nothing now; only the historical conflict remains

    repo.delete()

    assert not RegisteredRepository.objects.filter(pk=repo.pk).exists()
    conflict.refresh_from_db()
    assert conflict.repository_id is None
    assert conflict.repo_full_name == "test-source/org/repo"
