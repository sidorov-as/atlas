"""End-to-end walk-through of the settled scenario table from the design
conversation:

1. a repo drops a declaration -> the entity becomes removed
2. the repo re-declares it -> the entity is revived
3. a different repo tries to claim the same name while removed -> rejected
   with `removed_entity`
4. a mistakenly-created entity with no references is removed then purged
   trivially
5. a removed entity still referenced is purge-blocked
6. a removed entity referenced only by removed things purges with cascade

Each scenario below already has focused unit coverage elsewhere
(`atlas_plugin_ingestion`'s `test_ingestion.py`/`test_arbitration.py`,
`test_entity_removal_lifecycle.py`'s purge tests) — this file's job is to
walk the whole table end to end, in the same shape the design conversation
settled it, using the real ingestion pipeline and Entity Service rather than
re-deriving each piece in isolation.
"""

import pytest
from atlas_plugin_api import (
    KIND_SYSTEM,
    SOURCE_YAML,
    STATUS_ACTIVE,
    STATUS_REMOVED,
    get_catalog_entity_model,
    get_entity_service,
)
from atlas_plugin_ingestion.claims import claiming_repository_id
from atlas_plugin_ingestion.models import ConflictRecord, RegisteredRepository
from atlas_plugin_ingestion.pipeline import _ingest_manifest
from atlas_plugin_ingestion.upsert import ClaimRejected, upsert_entity
from atlas_plugin_ingestion.validation import validate_manifest_document

from server.apps.catalog.kinds import ValidateDeleteError
from server.apps.catalog.models import CatalogEntity, PurgeGrant
from server.apps.catalog.tests.factories import (
    create_component,
    create_resource,
)

pytestmark = pytest.mark.django_db

SYSTEM_MANIFEST = b"""
apiVersion: atlas/v1alpha1
kind: System
metadata:
  name: checkout
spec:
  owner: group:platform
"""

TWO_SYSTEMS_MANIFEST = b"""
apiVersion: atlas/v1alpha1
kind: System
metadata:
  name: checkout
spec:
  owner: group:platform
---
apiVersion: atlas/v1alpha1
kind: System
metadata:
  name: billing
spec:
  owner: group:platform
"""


def _system_doc(name: str):
    return validate_manifest_document(
        {
            "apiVersion": "atlas/v1alpha1",
            "kind": "System",
            "metadata": {"name": name},
            "spec": {"owner": "group:platform"},
        },
    )


def test_scenario_1_repo_drops_a_declaration_and_the_entity_is_removed(group):
    repo = RegisteredRepository.objects.create(
        source_id="test-source", path="org/repo"
    )
    _ingest_manifest(repo, "catalog-info.yaml", TWO_SYSTEMS_MANIFEST)
    billing = get_catalog_entity_model().objects.get(
        kind=KIND_SYSTEM, name="billing"
    )
    assert billing.status == STATUS_ACTIVE

    _ingest_manifest(
        repo, "catalog-info.yaml", SYSTEM_MANIFEST
    )  # billing no longer declared

    billing.refresh_from_db()
    assert billing.status == STATUS_REMOVED
    # Not a zombie, not a hard delete: the row survives, untouched otherwise.
    assert CatalogEntity.objects.filter(pk=billing.id).exists()


def test_scenario_2_repo_re_declares_and_the_entity_is_revived(group):
    repo = RegisteredRepository.objects.create(
        source_id="test-source", path="org/repo"
    )
    _ingest_manifest(repo, "catalog-info.yaml", TWO_SYSTEMS_MANIFEST)
    original_id = (
        get_catalog_entity_model()
        .objects.get(kind=KIND_SYSTEM, name="billing")
        .id
    )
    _ingest_manifest(repo, "catalog-info.yaml", SYSTEM_MANIFEST)  # dropped
    assert (
        get_catalog_entity_model()
        .objects.get(kind=KIND_SYSTEM, name="billing")
        .status
        == STATUS_REMOVED
    )

    _ingest_manifest(
        repo, "catalog-info.yaml", TWO_SYSTEMS_MANIFEST
    )  # re-declared

    billing = get_catalog_entity_model().objects.get(
        kind=KIND_SYSTEM, name="billing"
    )
    assert billing.status == STATUS_ACTIVE
    assert billing.id == original_id  # same identity, never a new entity


def test_scenario_3_a_different_repo_claiming_the_removed_name_is_rejected(
    group,
):
    repo = RegisteredRepository.objects.create(
        source_id="test-source", path="org/repo"
    )
    other_repo = RegisteredRepository.objects.create(
        source_id="test-source", path="org/other-repo"
    )
    claimed = upsert_entity(_system_doc("checkout"), repo)
    get_entity_service().remove(
        entity_id=claimed.id, actor=None, source=SOURCE_YAML
    )

    with pytest.raises(ClaimRejected):
        upsert_entity(_system_doc("checkout"), other_repo)

    claimed.refresh_from_db()
    assert claimed.status == STATUS_REMOVED
    # the original claim is untouched
    assert claiming_repository_id(claimed) == repo.id
    conflict = ConflictRecord.objects.get(
        kind="system", name="checkout", repository=other_repo
    )
    assert conflict.reason == ConflictRecord.REASON_REMOVED_ENTITY


def test_scenario_4_mistake_with_no_references_removed_then_purged_trivially(
    group, owner_user, owner_account
):
    mistake = create_resource(name="oops-typo", owner=group)
    PurgeGrant.objects.create(group=group, grantee=owner_account)

    get_entity_service().remove(entity_id=mistake.id, actor=owner_account)
    get_entity_service().purge(entity_id=mistake.id, actor=owner_account)

    assert not CatalogEntity.objects.filter(pk=mistake.id).exists()


def test_scenario_5_a_removed_entity_still_referenced_is_purge_blocked(
    group, system, owner_user, owner_account
):
    resource = create_resource(name="primary-db", owner=group)
    create_component(
        name="checkout-service",
        owner=group,
        system=system,
        depends_on=[resource],
    )
    PurgeGrant.objects.create(group=group, grantee=owner_account)

    get_entity_service().remove(entity_id=resource.id, actor=owner_account)
    with pytest.raises(ValidateDeleteError, match="still referenced"):
        get_entity_service().purge(entity_id=resource.id, actor=owner_account)

    assert CatalogEntity.objects.filter(pk=resource.id).exists()


def test_scenario_6_removed_entity_referenced_by_removed_purges_with_cascade(
    group,
    system,
    owner_user,
    owner_account,
):
    resource = create_resource(name="primary-db", owner=group)
    dependent = create_component(
        name="checkout-service",
        owner=group,
        system=system,
        depends_on=[resource],
    )
    PurgeGrant.objects.create(group=group, grantee=owner_account)

    get_entity_service().remove(entity_id=resource.id, actor=owner_account)
    get_entity_service().remove(
        entity_id=dependent.id, actor=owner_account
    )  # the only remaining reference is now removed too

    get_entity_service().purge(entity_id=resource.id, actor=owner_account)

    assert not CatalogEntity.objects.filter(pk=resource.id).exists()
    assert not dependent.component_details.depends_on.filter(
        pk=resource.id
    ).exists()
