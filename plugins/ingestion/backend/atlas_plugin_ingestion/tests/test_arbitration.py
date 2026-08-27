"""Ingestion claim arbitration.

Exercises `upsert_entity` directly for each arbitration branch, and
`_ingest_repository` for run-scoped behaviour (unblocking on delete,
intra-repo duplicate rejection) that spans multiple manifests.
"""

import pytest
from atlas_plugin_api import (
    KIND_SYSTEM,
    SOURCE_MANUAL,
    SOURCE_YAML,
    STATUS_ACTIVE,
    STATUS_REMOVED,
    get_catalog_entity_model,
    get_entity_service,
)
from django.contrib.auth import get_user_model
from server.apps.catalog.tests.factories import create_system

from atlas_plugin_ingestion.models import ConflictRecord, RegisteredRepository
from atlas_plugin_ingestion.pipeline import _ingest_repository
from atlas_plugin_ingestion.upsert import ClaimRejected, upsert_entity
from atlas_plugin_ingestion.validation import validate_manifest_document

pytestmark = pytest.mark.django_db


def _superuser():
    return get_user_model().objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="password123",
    )


def _system_doc(name: str, owner_ref: str = "group:platform"):
    return validate_manifest_document(
        {
            "apiVersion": "atlas/v1alpha1",
            "kind": "System",
            "metadata": {"name": name},
            "spec": {"owner": owner_ref},
        },
    )


class _FakeConnector:
    """Serves fixed manifest paths/content for one repo, no network calls."""

    def __init__(self, files: dict[str, bytes]):
        self._files = files

    def get_head_sha(self, repo):
        return "sha"

    def list_manifest_paths(self, repo):
        return list(self._files)

    def fetch_file(self, repo, path, sha):
        return self._files[path]


def test_yaml_claims_an_unclaimed_ref(repo, group):
    instance = upsert_entity(_system_doc("user-management"), repo)

    assert instance.source_kind == SOURCE_YAML
    assert instance.ingested_from_id == repo.id


def test_yaml_collides_with_a_manual_entity(repo, group):
    manual = create_system(name="user-management", owner=group)

    with pytest.raises(ClaimRejected):
        upsert_entity(_system_doc("user-management"), repo)

    manual.refresh_from_db()
    assert manual.source_kind == SOURCE_MANUAL
    assert manual.title == ""

    conflict = ConflictRecord.objects.get(kind="system", name="user-management")
    assert conflict.reason == ConflictRecord.REASON_MANUAL_ENTITY
    assert conflict.repo_full_name == str(repo)
    assert conflict.is_active is True


def test_same_repo_reclaims_its_own_entity(repo, group):
    first = upsert_entity(_system_doc("user-management"), repo)

    updated = upsert_entity(_system_doc("user-management"), repo)

    assert updated.id == first.id
    assert (
        get_catalog_entity_model()
        .objects.filter(kind=KIND_SYSTEM, name="user-management")
        .count()
        == 1
    )


def test_different_repo_collides_with_an_existing_yaml_claim(repo, group):
    other_repo = RegisteredRepository.objects.create(
        source_id="test-source", path="org/other-repo"
    )
    claimed = upsert_entity(_system_doc("user-management"), repo)

    with pytest.raises(ClaimRejected):
        upsert_entity(_system_doc("user-management"), other_repo)

    claimed.refresh_from_db()
    assert claimed.ingested_from_id == repo.id

    conflict = ConflictRecord.objects.get(
        kind="system", name="user-management", repository=other_repo
    )
    assert conflict.reason == ConflictRecord.REASON_OTHER_REPOSITORY
    assert conflict.is_active is True


def test_deleting_the_blocking_manual_entity_unblocks_the_rival_claim(repo, group):
    manual = create_system(name="user-management", owner=group)
    with pytest.raises(ClaimRejected):
        upsert_entity(_system_doc("user-management"), repo)

    manual.delete()

    instance = upsert_entity(_system_doc("user-management"), repo)
    assert instance.source_kind == SOURCE_YAML

    conflict = ConflictRecord.objects.get(kind="system", name="user-management")
    assert conflict.is_active is False


def test_a_different_repo_cannot_claim_a_ref_held_by_a_removed_yaml_entity(repo, group):
    other_repo = RegisteredRepository.objects.create(
        source_id="test-source", path="org/other-repo"
    )
    claimed = upsert_entity(_system_doc("user-management"), repo)
    get_entity_service().remove(entity_id=claimed.id, actor=None, source=SOURCE_YAML)

    with pytest.raises(ClaimRejected):
        upsert_entity(_system_doc("user-management"), other_repo)

    claimed.refresh_from_db()
    assert claimed.status == STATUS_REMOVED
    assert claimed.ingested_from_id == repo.id

    conflict = ConflictRecord.objects.get(
        kind="system", name="user-management", repository=other_repo
    )
    assert conflict.reason == ConflictRecord.REASON_REMOVED_ENTITY
    assert conflict.is_active is True


def test_a_removed_manual_entity_blocks_a_rival_yaml_claim_with_removed_entity_reason(
    repo, group
):
    manual = create_system(name="user-management", owner=group)
    get_entity_service().remove(entity_id=manual.id, actor=_superuser())

    with pytest.raises(ClaimRejected):
        upsert_entity(_system_doc("user-management"), repo)

    conflict = ConflictRecord.objects.get(kind="system", name="user-management")
    assert conflict.reason == ConflictRecord.REASON_REMOVED_ENTITY
    assert conflict.repo_full_name == str(repo)


def test_same_repo_redeclaring_its_own_removed_entity_is_not_a_rival_conflict(
    repo, group
):
    """Regression guard: the removed_entity rival check must not fire for the
    same-repo revive path (upsert_entity's own transaction handles that case
    separately)."""
    claimed = upsert_entity(_system_doc("user-management"), repo)
    get_entity_service().remove(entity_id=claimed.id, actor=None, source=SOURCE_YAML)

    revived = upsert_entity(_system_doc("user-management"), repo)

    assert revived.id == claimed.id
    assert revived.status == STATUS_ACTIVE
    assert not ConflictRecord.objects.filter(
        kind="system",
        name="user-management",
        reason=ConflictRecord.REASON_REMOVED_ENTITY,
    ).exists()


def test_claim_succeeds_once_the_removed_blocking_entity_is_purged(repo, group):
    """No cache-invalidation step required (arbitration is never cached) —
    arbitration is re-evaluated from
    current state on every call."""
    other_repo = RegisteredRepository.objects.create(
        source_id="test-source", path="org/other-repo"
    )
    claimed = upsert_entity(_system_doc("user-management"), repo)
    get_entity_service().remove(entity_id=claimed.id, actor=None, source=SOURCE_YAML)
    with pytest.raises(ClaimRejected):
        upsert_entity(_system_doc("user-management"), other_repo)

    get_entity_service().purge(entity_id=claimed.id, actor=_superuser())

    instance = upsert_entity(_system_doc("user-management"), other_repo)
    assert instance.source_kind == SOURCE_YAML
    assert instance.ingested_from_id == other_repo.id
    assert (
        instance.id != claimed.id
    )  # a genuinely new identity (D3), not a resurrection

    conflict = ConflictRecord.objects.get(
        kind="system", name="user-management", repository=other_repo
    )
    assert conflict.is_active is False


def test_intra_repo_duplicate_ref_is_rejected_for_both_declarations(repo, group):
    manifest = b"""
apiVersion: atlas/v1alpha1
kind: System
metadata:
  name: user-management
  title: First declaration
spec:
  owner: group:platform
"""
    duplicate_manifest = b"""
apiVersion: atlas/v1alpha1
kind: System
metadata:
  name: user-management
  title: Second declaration
spec:
  owner: group:platform
"""
    connector = _FakeConnector(
        {"a/catalog-info.yaml": manifest, "b/catalog-info.yaml": duplicate_manifest},
    )

    _ingest_repository(connector, repo)

    assert (
        not get_catalog_entity_model()
        .objects.filter(kind=KIND_SYSTEM, name="user-management")
        .exists()
    )
