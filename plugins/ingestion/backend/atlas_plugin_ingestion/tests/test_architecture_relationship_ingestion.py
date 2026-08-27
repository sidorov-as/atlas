"""Ingestion tests for declared `spec.relationships` -> YAML-origin Architecture
Relationships (catalog-ingestion spec)."""

import pytest
from atlas_plugin_api import (
    KIND_COMPONENT,
    get_architecture_relationship_model,
    get_catalog_entity_model,
)

from atlas_plugin_ingestion.pipeline import _ingest_manifest

pytestmark = pytest.mark.django_db

ArchitectureRelationship = get_architecture_relationship_model()

# `customer-portal` declares its relationship to `api-gateway` before that
# target is defined later in the same multi-document manifest.
BASE_MANIFEST = b"""
apiVersion: atlas/v1alpha1
kind: System
metadata:
  name: user-management
spec:
  owner: group:platform
---
apiVersion: atlas/v1alpha1
kind: Component
metadata:
  name: customer-portal
spec:
  type: website
  lifecycle: production
  owner: group:platform
  system: system:user-management
  relationships:
    - target: component:api-gateway
      label: Makes API calls to
      technology: REST/HTTPS
      interactionKind: synchronous
      tags: [runtime]
---
apiVersion: atlas/v1alpha1
kind: Component
metadata:
  name: api-gateway
spec:
  type: service
  lifecycle: production
  owner: group:platform
  system: system:user-management
"""

NO_RELATIONSHIP_MANIFEST = BASE_MANIFEST.replace(
    b"""  relationships:
    - target: component:api-gateway
      label: Makes API calls to
      technology: REST/HTTPS
      interactionKind: synchronous
      tags: [runtime]
""",
    b"",
)

MALFORMED_MANIFEST = b"""
apiVersion: atlas/v1alpha1
kind: System
metadata:
  name: user-management
spec:
  owner: group:platform
---
apiVersion: atlas/v1alpha1
kind: Component
metadata:
  name: bad-relationship-component
spec:
  type: service
  lifecycle: production
  owner: group:platform
  system: system:user-management
  relationships:
    - target: component:api-gateway
      label: ""
      interactionKind: carrier-pigeon
---
apiVersion: atlas/v1alpha1
kind: Component
metadata:
  name: api-gateway
spec:
  type: service
  lifecycle: production
  owner: group:platform
  system: system:user-management
"""

UNRESOLVED_TARGET_MANIFEST = b"""
apiVersion: atlas/v1alpha1
kind: System
metadata:
  name: user-management
spec:
  owner: group:platform
---
apiVersion: atlas/v1alpha1
kind: Component
metadata:
  name: customer-portal
spec:
  type: website
  lifecycle: production
  owner: group:platform
  system: system:user-management
  relationships:
    - target: component:does-not-exist
      label: Calls missing service
    - target: component:api-gateway
      label: Makes API calls to
---
apiVersion: atlas/v1alpha1
kind: Component
metadata:
  name: api-gateway
spec:
  type: service
  lifecycle: production
  owner: group:platform
  system: system:user-management
"""


def test_declared_relationship_is_created_as_yaml_origin(repo, group):
    _ingest_manifest(repo, "catalog-info.yaml", BASE_MANIFEST)

    source = get_catalog_entity_model().objects.get(
        kind=KIND_COMPONENT, name="customer-portal"
    )
    target = get_catalog_entity_model().objects.get(
        kind=KIND_COMPONENT, name="api-gateway"
    )
    relationship = ArchitectureRelationship.objects.get(source=source, target=target)
    assert relationship.origin == "yaml"
    assert relationship.label == "Makes API calls to"
    assert relationship.technology == "REST/HTTPS"
    assert relationship.interaction_kind == "synchronous"
    assert relationship.tags == ["runtime"]


def test_relationship_target_defined_later_in_same_manifest_is_resolved(repo, group):
    # `customer-portal` (which declares the relationship) precedes its target
    # `api-gateway` in BASE_MANIFEST's document order.
    _ingest_manifest(repo, "catalog-info.yaml", BASE_MANIFEST)

    assert (
        ArchitectureRelationship.objects.filter(
            source__kind=KIND_COMPONENT,
            target__kind=KIND_COMPONENT,
            origin="yaml",
        ).count()
        == 1
    )


def test_reingestion_without_declaration_removes_yaml_relationship_but_not_manual(
    repo, group
):
    _ingest_manifest(repo, "catalog-info.yaml", BASE_MANIFEST)
    source = get_catalog_entity_model().objects.get(
        kind=KIND_COMPONENT, name="customer-portal"
    )
    target = get_catalog_entity_model().objects.get(
        kind=KIND_COMPONENT, name="api-gateway"
    )

    manual = ArchitectureRelationship.objects.create(
        source=source,
        target=target,
        label="Manual note",
        origin="manual",
    )

    _ingest_manifest(repo, "catalog-info.yaml", NO_RELATIONSHIP_MANIFEST)

    assert not ArchitectureRelationship.objects.filter(origin="yaml").exists()
    manual.refresh_from_db()
    assert manual.label == "Manual note"


def test_malformed_relationship_fields_reject_the_whole_document(repo, group):
    _ingest_manifest(repo, "catalog-info.yaml", MALFORMED_MANIFEST)

    assert (
        not get_catalog_entity_model()
        .objects.filter(kind=KIND_COMPONENT, name="bad-relationship-component")
        .exists()
    )
    assert (
        get_catalog_entity_model()
        .objects.filter(kind=KIND_COMPONENT, name="api-gateway")
        .exists()
    )
    assert not ArchitectureRelationship.objects.exists()


def test_unresolved_relationship_target_is_skipped_without_blocking_entity_or_other_declarations(
    repo, group
):
    _ingest_manifest(repo, "catalog-info.yaml", UNRESOLVED_TARGET_MANIFEST)

    source = get_catalog_entity_model().objects.get(
        kind=KIND_COMPONENT, name="customer-portal"
    )
    assert (
        get_catalog_entity_model()
        .objects.filter(kind=KIND_COMPONENT, name="api-gateway")
        .exists()
    )

    relationships = ArchitectureRelationship.objects.filter(source=source)
    assert relationships.count() == 1
    assert relationships.get().label == "Makes API calls to"
