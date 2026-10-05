"""Ingestion pipeline tests.

Exercises `_ingest_manifest` directly — the per-manifest-document flow the
poll loop drives (parse -> validate -> upsert), without touching the network
(`GitConnector` isn't invoked here; that's `run_ingestion_pass`'s job).
"""

from unittest.mock import patch

import pytest
from atlas_plugin_api import (
    KIND_ACTOR,
    KIND_COMPONENT,
    KIND_SYSTEM,
    SOURCE_YAML,
    STATUS_ACTIVE,
    STATUS_REMOVED,
    SafeHttpResponse,
    get_catalog_entity_model,
)
from server.apps.catalog.tests.factories import create_system

from atlas_plugin_ingestion.claims import claiming_repository_id
from atlas_plugin_ingestion.models import RegisteredRepository
from atlas_plugin_ingestion.pipeline import _ingest_manifest

pytestmark = pytest.mark.django_db

SPEC_FETCH_PATCH_TARGET = "atlas_plugin_apis.spec_fetch.safe_request"

SYSTEM_MANIFEST = b"""
apiVersion: atlas/v1alpha1
kind: System
metadata:
  name: user-management
  title: User Management
  documentation: |
    ## User accounts

    Manages account lifecycle and authentication.
spec:
  owner: group:platform
"""


def test_first_ingest_creates_entity(repo, group):
    _ingest_manifest(repo, "catalog-info.yaml", SYSTEM_MANIFEST)

    system = get_catalog_entity_model().objects.get(
        kind=KIND_SYSTEM, name="user-management"
    )
    assert system.title == "User Management"
    assert (
        system.documentation
        == "## User accounts\n\nManages account lifecycle and authentication.\n"
    )
    assert claiming_repository_id(system) == repo.id


def test_reingest_updates_the_same_entity_in_place(repo, group):
    _ingest_manifest(repo, "catalog-info.yaml", SYSTEM_MANIFEST)
    first = get_catalog_entity_model().objects.get(
        kind=KIND_SYSTEM, name="user-management"
    )

    updated_manifest = SYSTEM_MANIFEST.replace(
        b"User Management", b"User Management Team"
    )
    _ingest_manifest(repo, "catalog-info.yaml", updated_manifest)

    assert (
        get_catalog_entity_model()
        .objects.filter(kind=KIND_SYSTEM, name="user-management")
        .count()
        == 1
    )
    second = get_catalog_entity_model().objects.get(
        kind=KIND_SYSTEM, name="user-management"
    )
    assert second.id == first.id
    assert second.title == "User Management Team"


def test_reingest_updates_documentation(repo, group):
    _ingest_manifest(repo, "catalog-info.yaml", SYSTEM_MANIFEST)
    updated_manifest = SYSTEM_MANIFEST.replace(
        b"Manages account lifecycle and authentication.",
        b"Contains the current account runbook.",
    )
    _ingest_manifest(repo, "catalog-info.yaml", updated_manifest)

    assert (
        get_catalog_entity_model()
        .objects.get(
            kind=KIND_SYSTEM,
            name="user-management",
        )
        .documentation
        == "## User accounts\n\nContains the current account runbook.\n"
    )


def test_reingest_replaces_described_document_links(repo, group):
    manifest = SYSTEM_MANIFEST.replace(
        b"spec:",
        b"""  links:
    - url: https://docs.example.test/runbook
      title: Runbook
      description: Operating guide
      type: runbook
    - url: https://docs.example.test/dashboard
      title: Dashboard
spec:""",
    )
    _ingest_manifest(repo, "catalog-info.yaml", manifest)
    system = get_catalog_entity_model().objects.get(
        kind=KIND_SYSTEM, name="user-management"
    )
    assert system.links[0]["description"] == "Operating guide"

    _ingest_manifest(repo, "catalog-info.yaml", SYSTEM_MANIFEST)
    system.refresh_from_db()
    assert system.links == []


def test_invalid_document_is_skipped_without_affecting_others(repo, group):
    manifest = b"""
apiVersion: atlas/v1alpha1
kind: System
metadata:
  name: valid-system
spec:
  owner: group:platform
---
apiVersion: atlas/v1alpha1
kind: System
metadata:
  name: invalid-system
spec: {}
"""
    _ingest_manifest(repo, "catalog-info.yaml", manifest)

    assert (
        get_catalog_entity_model()
        .objects.filter(kind=KIND_SYSTEM, name="valid-system")
        .exists()
    )
    assert (
        not get_catalog_entity_model()
        .objects.filter(kind=KIND_SYSTEM, name="invalid-system")
        .exists()
    )


def test_multi_document_manifest_ingests_all_entities(repo, group):
    manifest = b"""
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
  name: user-api-service
spec:
  type: service
  lifecycle: production
  owner: group:platform
  system: system:user-management
---
apiVersion: atlas/v1alpha1
kind: Component
metadata:
  name: user-web-frontend
spec:
  type: website
  lifecycle: production
  owner: group:platform
  system: system:user-management
"""
    _ingest_manifest(repo, "catalog-info.yaml", manifest)

    assert (
        get_catalog_entity_model()
        .objects.filter(kind=KIND_SYSTEM, name="user-management")
        .exists()
    )
    assert (
        get_catalog_entity_model()
        .objects.filter(kind=KIND_COMPONENT, name="user-api-service")
        .exists()
    )
    assert (
        get_catalog_entity_model()
        .objects.filter(kind=KIND_COMPONENT, name="user-web-frontend")
        .exists()
    )


API_INLINE_SPEC_MANIFEST = b"""
apiVersion: atlas/v1alpha1
kind: System
metadata:
  name: user-management
spec:
  owner: group:platform
---
apiVersion: atlas/v1alpha1
kind: API
metadata:
  name: inline-api
spec:
  type: openapi
  owner: group:platform
  system: system:user-management
  specSource: inline
  specContent: "openapi: 3.0.0"
"""


def test_manifest_with_inline_spec_source_is_ingested(repo, group):
    _ingest_manifest(repo, "catalog-info.yaml", API_INLINE_SPEC_MANIFEST)

    api = get_catalog_entity_model().objects.get(kind="api", name="inline-api")
    assert api.api_details.spec_source == "inline"
    assert api.api_details.spec_content == "openapi: 3.0.0"


API_URL_SPEC_MANIFEST = b"""
apiVersion: atlas/v1alpha1
kind: System
metadata:
  name: user-management
spec:
  owner: group:platform
---
apiVersion: atlas/v1alpha1
kind: API
metadata:
  name: url-api
spec:
  type: openapi
  owner: group:platform
  system: system:user-management
  specSource: url
  specUrl: https://example.com/openapi.yaml
"""


def test_manifest_with_url_spec_source_is_ingested_and_resolved(repo, group):
    with patch(SPEC_FETCH_PATCH_TARGET) as mock_get:
        mock_get.return_value = SafeHttpResponse(
            status_code=200,
            headers={},
            url="https://example.com/openapi.yaml",
            resolved_address="203.0.113.1",
            content=b"openapi: 3.0.0",
        )
        _ingest_manifest(repo, "catalog-info.yaml", API_URL_SPEC_MANIFEST)

    api = get_catalog_entity_model().objects.get(kind="api", name="url-api")
    assert api.api_details.spec_source == "url"
    assert api.api_details.spec_url == "https://example.com/openapi.yaml"
    assert api.api_details.spec_content == "openapi: 3.0.0"
    assert api.api_details.spec_resolve_failed is False


ACTOR_MANIFEST = b"""
apiVersion: atlas/v1alpha1
kind: User
metadata:
  name: jdoe
spec:
  displayName: Jane Doe
  email: jdoe@example.com
"""


def test_actor_declared_via_manifest_is_ingested(repo):
    """Actor becomes ingestible; Team does not."""
    _ingest_manifest(repo, "catalog-info.yaml", ACTOR_MANIFEST)

    actor = get_catalog_entity_model().objects.get(kind=KIND_ACTOR, name="jdoe")
    assert actor.actor_details.display_name == "Jane Doe"
    assert actor.actor_details.email == "jdoe@example.com"
    assert claiming_repository_id(actor) == repo.id
    assert actor.source_kind == SOURCE_YAML


def test_reingest_updates_the_same_actor_in_place(repo):
    _ingest_manifest(repo, "catalog-info.yaml", ACTOR_MANIFEST)
    first = get_catalog_entity_model().objects.get(kind=KIND_ACTOR, name="jdoe")

    updated_manifest = ACTOR_MANIFEST.replace(b"Jane Doe", b"Jane R. Doe")
    _ingest_manifest(repo, "catalog-info.yaml", updated_manifest)

    assert (
        get_catalog_entity_model().objects.filter(kind=KIND_ACTOR, name="jdoe").count()
        == 1
    )
    second = get_catalog_entity_model().objects.get(kind=KIND_ACTOR, name="jdoe")
    assert second.id == first.id
    assert second.actor_details.display_name == "Jane R. Doe"


# Zombie-entity reconciliation —
# a whole entity dropped from a re-ingested manifest becomes `removed`, not
# left silently `active`; re-declaring it revives it in place; auto-remove
# authority stays sticky to the claiming repository's own origin.

TWO_SYSTEMS_MANIFEST = b"""
apiVersion: atlas/v1alpha1
kind: System
metadata:
  name: user-management
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


def test_dropped_declaration_removes_not_zombifies_entity(repo, group):
    _ingest_manifest(repo, "catalog-info.yaml", TWO_SYSTEMS_MANIFEST)
    billing = get_catalog_entity_model().objects.get(kind=KIND_SYSTEM, name="billing")
    assert billing.status == STATUS_ACTIVE

    _ingest_manifest(
        repo, "catalog-info.yaml", SYSTEM_MANIFEST
    )  # only user-management now

    billing.refresh_from_db()
    assert billing.status == STATUS_REMOVED
    # Not a zombie and not a hard delete: the row (and its kind-details) survive.
    assert (
        get_catalog_entity_model()
        .objects.filter(kind=KIND_SYSTEM, name="billing")
        .exists()
    )


def test_readded_declaration_revives_entity_preserving_id(repo, group):
    _ingest_manifest(repo, "catalog-info.yaml", TWO_SYSTEMS_MANIFEST)
    original_id = (
        get_catalog_entity_model().objects.get(kind=KIND_SYSTEM, name="billing").id
    )

    _ingest_manifest(repo, "catalog-info.yaml", SYSTEM_MANIFEST)
    assert (
        get_catalog_entity_model().objects.get(kind=KIND_SYSTEM, name="billing").status
        == STATUS_REMOVED
    )

    _ingest_manifest(repo, "catalog-info.yaml", TWO_SYSTEMS_MANIFEST)

    billing = get_catalog_entity_model().objects.get(kind=KIND_SYSTEM, name="billing")
    assert billing.status == STATUS_ACTIVE
    assert billing.id == original_id


def test_manual_entity_sharing_unclaimed_ref_is_untouched(repo, group):
    """Ingestion cannot remove a manually-created Component —
    a manual entity was never this repo's claim, so reconciliation never looks at it."""
    manual = create_system(name="legacy-reporting", owner=group)

    _ingest_manifest(
        repo, "catalog-info.yaml", SYSTEM_MANIFEST
    )  # unrelated to legacy-reporting

    manual.refresh_from_db()
    assert manual.status == STATUS_ACTIVE
    assert claiming_repository_id(manual) is None


def test_other_repositorys_claim_is_unaffected_by_this_repos_reconciliation(
    repo, group
):
    other_repo = RegisteredRepository.objects.create(
        source_id="test-source", path="org/other-repo"
    )
    _ingest_manifest(other_repo, "catalog-info.yaml", SYSTEM_MANIFEST)
    claimed_by_other = get_catalog_entity_model().objects.get(
        kind=KIND_SYSTEM, name="user-management"
    )
    assert claiming_repository_id(claimed_by_other) == other_repo.id

    unrelated_manifest = SYSTEM_MANIFEST.replace(
        b"user-management", b"unrelated-system"
    )
    _ingest_manifest(repo, "catalog-info.yaml", unrelated_manifest)

    claimed_by_other.refresh_from_db()
    assert claimed_by_other.status == STATUS_ACTIVE
