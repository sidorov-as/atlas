"""`kind: Include` recognition and expansion.

Exercises `_ingest_repository` end to end with a `_FakeConnector` that also
implements `list_paths` (needed to resolve glob `spec.paths` entries), no
network involved.
"""

import pytest
from atlas_plugin_api import (
    KIND_API,
    KIND_COMPONENT,
    KIND_SYSTEM,
    get_catalog_entity_model,
)

from atlas_plugin_ingestion.models import IngestionIssue
from atlas_plugin_ingestion.pipeline import _ingest_repository

pytestmark = pytest.mark.django_db


class _FakeConnector:
    """Serves fixed manifest/fragment paths and content for one repo, with
    no network calls. `files` covers every path that might be fetched or
    globbed; `manifest_paths` is the (possibly narrower) subset that
    `list_manifest_paths` (ordinary tree-walk discovery) returns."""

    def __init__(
        self, files: dict[str, bytes], manifest_paths: list[str] | None = None
    ):
        self._files = files
        self._manifest_paths = (
            manifest_paths
            if manifest_paths is not None
            else [
                path for path in files if path.rsplit("/", 1)[-1] == "catalog-info.yaml"
            ]
        )

    def get_head_sha(self, repo):
        return "sha"

    def list_manifest_paths(self, repo):
        return list(self._manifest_paths)

    def list_paths(self, repo):
        return list(self._files)

    def fetch_file(self, repo, path, sha):
        return self._files[path]


def _system_manifest(name: str) -> bytes:
    return f"""
apiVersion: atlas/v1alpha1
kind: System
metadata:
  name: {name}
spec:
  owner: group:platform
""".encode()


def test_single_include_composes_a_fragment_into_the_pool(repo, group):
    top = b"""
kind: Include
spec:
  paths:
    - .manifests/db-catalog-info.yaml
---
apiVersion: atlas/v1alpha1
kind: System
metadata:
  name: payments
spec:
  owner: group:platform
"""
    connector = _FakeConnector(
        {
            "catalog-info.yaml": top,
            ".manifests/db-catalog-info.yaml": _system_manifest("payments-db"),
        }
    )

    _ingest_repository(connector, repo)

    assert (
        get_catalog_entity_model()
        .objects.filter(kind=KIND_SYSTEM, name="payments")
        .exists()
    )
    assert (
        get_catalog_entity_model()
        .objects.filter(kind=KIND_SYSTEM, name="payments-db")
        .exists()
    )


def test_include_document_is_never_validated_as_an_entity(repo, group):
    top = b"""
kind: Include
spec:
  paths: [.manifests/db-catalog-info.yaml]
"""
    connector = _FakeConnector(
        {
            "catalog-info.yaml": top,
            ".manifests/db-catalog-info.yaml": _system_manifest("payments-db"),
        }
    )

    _ingest_repository(connector, repo)

    assert not IngestionIssue.objects.filter(path="catalog-info.yaml").exists()


def test_relative_include_path_resolves_against_its_own_directory(repo, group):
    top = b"""
kind: Include
spec:
  paths: [.manifests/apis-catalog-info.yaml]
"""
    connector = _FakeConnector(
        {
            "services/payments/catalog-info.yaml": top,
            "services/payments/.manifests/apis-catalog-info.yaml": _system_manifest(
                "payments-api"
            ),
        }
    )

    _ingest_repository(connector, repo)

    assert (
        get_catalog_entity_model()
        .objects.filter(kind=KIND_SYSTEM, name="payments-api")
        .exists()
    )


def test_glob_include_expands_every_match(repo, group):
    top = b"""
kind: Include
spec:
  paths: [.manifests/*.yaml]
"""
    connector = _FakeConnector(
        {
            "catalog-info.yaml": top,
            ".manifests/a-catalog-info.yaml": _system_manifest("fragment-a"),
            ".manifests/b-catalog-info.yaml": _system_manifest("fragment-b"),
        }
    )

    _ingest_repository(connector, repo)

    assert (
        get_catalog_entity_model()
        .objects.filter(kind=KIND_SYSTEM, name="fragment-a")
        .exists()
    )
    assert (
        get_catalog_entity_model()
        .objects.filter(kind=KIND_SYSTEM, name="fragment-b")
        .exists()
    )


def test_glob_does_not_reach_into_nested_subdirectories(repo, group):
    top = b"""
kind: Include
spec:
  paths: [.manifests/*.yaml]
"""
    connector = _FakeConnector(
        {
            "catalog-info.yaml": top,
            ".manifests/nested/deep-catalog-info.yaml": _system_manifest("too-deep"),
        }
    )

    _ingest_repository(connector, repo)

    assert (
        not get_catalog_entity_model()
        .objects.filter(kind=KIND_SYSTEM, name="too-deep")
        .exists()
    )
    assert IngestionIssue.objects.filter(is_active=True).exists()


def test_nested_include_is_expanded_recursively(repo, group):
    top = b"""
kind: Include
spec:
  paths: [.manifests/a.yaml]
"""
    fragment_a = b"""
kind: Include
spec:
  paths: [b.yaml]
"""
    connector = _FakeConnector(
        {
            "catalog-info.yaml": top,
            ".manifests/a.yaml": fragment_a,
            ".manifests/b.yaml": _system_manifest("deeply-nested"),
        }
    )

    _ingest_repository(connector, repo)

    assert (
        get_catalog_entity_model()
        .objects.filter(kind=KIND_SYSTEM, name="deeply-nested")
        .exists()
    )


def test_direct_cycle_is_detected_and_rejected(repo, group):
    a = b"""
kind: Include
spec:
  paths: [b.yaml]
"""
    b = b"""
kind: Include
spec:
  paths: [a.yaml]
---
apiVersion: atlas/v1alpha1
kind: System
metadata:
  name: survives-the-cycle
spec:
  owner: group:platform
"""
    connector = _FakeConnector(
        {".manifests/a.yaml": a, ".manifests/b.yaml": b},
        manifest_paths=[".manifests/a.yaml"],
    )

    _ingest_repository(connector, repo)

    assert (
        get_catalog_entity_model()
        .objects.filter(kind=KIND_SYSTEM, name="survives-the-cycle")
        .exists()
    )
    issue = IngestionIssue.objects.get(is_active=True)
    assert "cycle" in issue.message.lower()


def test_indirect_cycle_is_detected(repo, group):
    a = b"kind: Include\nspec:\n  paths: [b.yaml]\n"
    b = b"kind: Include\nspec:\n  paths: [c.yaml]\n"
    c = b"kind: Include\nspec:\n  paths: [a.yaml]\n"
    connector = _FakeConnector(
        {".manifests/a.yaml": a, ".manifests/b.yaml": b, ".manifests/c.yaml": c},
        manifest_paths=[".manifests/a.yaml"],
    )

    _ingest_repository(connector, repo)

    issue = IngestionIssue.objects.get(is_active=True)
    assert "cycle" in issue.message.lower()


def test_include_path_named_catalog_info_yaml_is_rejected(repo, group):
    top = b"""
kind: Include
spec:
  paths: [extra/catalog-info.yaml]
---
apiVersion: atlas/v1alpha1
kind: System
metadata:
  name: still-ingested
spec:
  owner: group:platform
"""
    connector = _FakeConnector(
        {
            "services/payments/catalog-info.yaml": top,
            "services/payments/extra/catalog-info.yaml": _system_manifest(
                "should-not-be-ingested-twice"
            ),
        },
        manifest_paths=["services/payments/catalog-info.yaml"],
    )

    _ingest_repository(connector, repo)

    assert (
        get_catalog_entity_model()
        .objects.filter(kind=KIND_SYSTEM, name="still-ingested")
        .exists()
    )
    assert (
        not get_catalog_entity_model()
        .objects.filter(
            kind=KIND_SYSTEM,
            name="should-not-be-ingested-twice",
        )
        .exists()
    )
    issue = IngestionIssue.objects.get(is_active=True)
    assert "catalog-info.yaml" in issue.message


def test_one_broken_include_path_does_not_block_the_rest(repo, group):
    top = b"""
kind: Include
spec:
  paths:
    - .manifests/exists.yaml
    - .manifests/missing.yaml
---
apiVersion: atlas/v1alpha1
kind: System
metadata:
  name: sibling-system
spec:
  owner: group:platform
"""
    connector = _FakeConnector(
        {
            "catalog-info.yaml": top,
            ".manifests/exists.yaml": _system_manifest("fragment-exists"),
        }
    )

    _ingest_repository(connector, repo)

    assert (
        get_catalog_entity_model()
        .objects.filter(kind=KIND_SYSTEM, name="sibling-system")
        .exists()
    )
    assert (
        get_catalog_entity_model()
        .objects.filter(kind=KIND_SYSTEM, name="fragment-exists")
        .exists()
    )
    issue = IngestionIssue.objects.get(is_active=True)
    assert "missing.yaml" in issue.message


# Unsafe `spec.paths` entries are rejected
# without blocking the rest of the manifest. Symlink-escape coverage lives in
# `test_git_connector.py` instead — a symlink that stays
# syntactically in-bounds can only be caught once a real checkout exists to
# resolve it against, which this pre-check (before any file is fetched) has
# no access to; see `paths.py`'s module docstring.


def test_absolute_include_path_is_rejected(repo, group):
    top = b"""
kind: Include
spec:
  paths: [/etc/passwd]
---
apiVersion: atlas/v1alpha1
kind: System
metadata:
  name: survives-the-absolute-path
spec:
  owner: group:platform
"""
    connector = _FakeConnector({"catalog-info.yaml": top})

    _ingest_repository(connector, repo)

    assert (
        get_catalog_entity_model()
        .objects.filter(kind=KIND_SYSTEM, name="survives-the-absolute-path")
        .exists()
    )
    issue = IngestionIssue.objects.get(is_active=True)
    assert "/etc/passwd" in issue.message


def test_traversal_include_path_is_rejected(repo, group):
    top = b"""
kind: Include
spec:
  paths: [../../etc/passwd]
---
apiVersion: atlas/v1alpha1
kind: System
metadata:
  name: survives-the-traversal
spec:
  owner: group:platform
"""
    connector = _FakeConnector({"catalog-info.yaml": top})

    _ingest_repository(connector, repo)

    assert (
        get_catalog_entity_model()
        .objects.filter(kind=KIND_SYSTEM, name="survives-the-traversal")
        .exists()
    )
    issue = IngestionIssue.objects.get(is_active=True)
    assert "../../etc/passwd" in issue.message


def test_include_fetch_failure_is_isolated(repo, group):
    top = b"""
kind: Include
spec:
  paths: [.manifests/unreachable.yaml]
---
apiVersion: atlas/v1alpha1
kind: System
metadata:
  name: sibling-system-2
spec:
  owner: group:platform
"""

    class _FailingFetchConnector(_FakeConnector):
        def fetch_file(self, repo, path, sha):
            if path == ".manifests/unreachable.yaml":
                raise ConnectionError("boom")
            return super().fetch_file(repo, path, sha)

    connector = _FailingFetchConnector({"catalog-info.yaml": top})

    _ingest_repository(connector, repo)

    assert (
        get_catalog_entity_model()
        .objects.filter(kind=KIND_SYSTEM, name="sibling-system-2")
        .exists()
    )
    issue = IngestionIssue.objects.get(is_active=True)
    assert issue.path == ".manifests/unreachable.yaml"


def test_mixed_include_and_entity_documents_in_one_file(repo, group):
    top = b"""
kind: Include
spec:
  paths: [.manifests/db-catalog-info.yaml]
---
apiVersion: atlas/v1alpha1
kind: System
metadata:
  name: mixed-file-system
spec:
  owner: group:platform
---
apiVersion: atlas/v1alpha1
kind: API
metadata:
  name: mixed-file-api
spec:
  type: openapi
  owner: group:platform
  system: system:mixed-file-system
  specSource: inline
  specContent: "openapi: 3.0.0"
"""
    connector = _FakeConnector(
        {
            "catalog-info.yaml": top,
            ".manifests/db-catalog-info.yaml": _system_manifest("mixed-file-fragment"),
        }
    )

    _ingest_repository(connector, repo)

    assert (
        get_catalog_entity_model()
        .objects.filter(kind=KIND_SYSTEM, name="mixed-file-system")
        .exists()
    )
    assert (
        get_catalog_entity_model()
        .objects.filter(kind=KIND_API, name="mixed-file-api")
        .exists()
    )
    assert (
        get_catalog_entity_model()
        .objects.filter(kind=KIND_SYSTEM, name="mixed-file-fragment")
        .exists()
    )


# Integration + regression coverage: a whole fragment
# directory pulled in alongside the including file's own entities in one
# run, and — now that Include expansion sits in front of every manifest's
# documents — a repository that uses none of it still behaves exactly as it
# did before Include expansion existed.


def test_top_level_manifest_including_a_fragment_directory_ingests_everything_in_one_run(
    repo, group
):
    top = b"""
kind: Include
spec:
  paths: [.manifests/*.yaml]
---
apiVersion: atlas/v1alpha1
kind: System
metadata:
  name: payments
spec:
  owner: group:platform
---
apiVersion: atlas/v1alpha1
kind: Component
metadata:
  name: payments-api
spec:
  type: service
  lifecycle: production
  owner: group:platform
  system: system:payments
"""
    connector = _FakeConnector(
        {
            "catalog-info.yaml": top,
            ".manifests/db-catalog-info.yaml": _system_manifest("payments-db"),
            ".manifests/cache-catalog-info.yaml": _system_manifest("payments-cache"),
        }
    )

    _ingest_repository(connector, repo)

    entities = get_catalog_entity_model().objects
    assert entities.filter(kind=KIND_SYSTEM, name="payments").exists()
    assert entities.filter(kind=KIND_COMPONENT, name="payments-api").exists()
    assert entities.filter(kind=KIND_SYSTEM, name="payments-db").exists()
    assert entities.filter(kind=KIND_SYSTEM, name="payments-cache").exists()
    assert not IngestionIssue.objects.filter(is_active=True).exists()


def test_scattered_discovery_and_plain_multi_document_manifests_are_unaffected(
    repo, group
):
    service_a = b"""
apiVersion: atlas/v1alpha1
kind: System
metadata:
  name: service-a
spec:
  owner: group:platform
"""
    service_b = b"""
apiVersion: atlas/v1alpha1
kind: System
metadata:
  name: service-b
spec:
  owner: group:platform
---
apiVersion: atlas/v1alpha1
kind: Component
metadata:
  name: service-b-api
spec:
  type: service
  lifecycle: production
  owner: group:platform
  system: system:service-b
"""
    connector = _FakeConnector(
        {
            "services/a/catalog-info.yaml": service_a,
            "services/b/catalog-info.yaml": service_b,
        }
    )

    _ingest_repository(connector, repo)

    entities = get_catalog_entity_model().objects
    assert entities.filter(kind=KIND_SYSTEM, name="service-a").exists()
    assert entities.filter(kind=KIND_SYSTEM, name="service-b").exists()
    assert entities.filter(kind=KIND_COMPONENT, name="service-b-api").exists()
    assert not IngestionIssue.objects.filter(is_active=True).exists()
