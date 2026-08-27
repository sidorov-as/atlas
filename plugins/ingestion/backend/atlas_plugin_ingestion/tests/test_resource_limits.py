"""Resource limits enforced at the ingestion fetch/parse boundary
an oversized fetched file is
rejected before parsing, excessively nested YAML is rejected, an `Include`
chain deeper than the configured maximum is rejected without a cycle
present, and a single run's total included-file count is bounded — in every
case, without blocking ingestion of the rest of the repository's manifests
(catalog-ingestion spec's "Fetched content is bounded before parsing";
ingestion-manifest-includes spec's "Include composition is recursive with
cycle detection").

Exercises `_ingest_repository` end to end with a `_FakeConnector`, no
network involved, with `atlas_plugin_ingestion.limits.resolved_limits`
monkeypatched to small values so each scenario stays cheap to construct —
`pipeline.py` and `database_schema.py` both resolve limits via that same
module-level function, so a single monkeypatch covers both (sourceSqlPath's
own oversized-file coverage lives in `test_database_schema.py` instead,
alongside its other independent-resolution tests).
"""

import pytest
from atlas_plugin_api import KIND_SYSTEM, get_catalog_entity_model

import atlas_plugin_ingestion.limits as limits_module
from atlas_plugin_ingestion.limits import IngestionLimits
from atlas_plugin_ingestion.models import IngestionIssue
from atlas_plugin_ingestion.pipeline import _ingest_repository

pytestmark = pytest.mark.django_db


class _FakeConnector:
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


def _small_limits(**overrides) -> IngestionLimits:
    return IngestionLimits(
        max_fetched_file_bytes=overrides.get("max_fetched_file_bytes", 4096),
        max_yaml_nesting_depth=overrides.get("max_yaml_nesting_depth", 50),
        max_include_depth=overrides.get("max_include_depth", 50),
        max_included_files=overrides.get("max_included_files", 500),
    )


def _patch_limits(monkeypatch, **overrides) -> None:
    monkeypatch.setattr(
        limits_module, "resolved_limits", lambda: _small_limits(**overrides)
    )


def test_oversized_manifest_is_rejected_before_parsing(repo, group, monkeypatch):
    _patch_limits(monkeypatch, max_fetched_file_bytes=500)

    oversized = b"kind: System\n" * 100  # well over the 500-byte limit
    connector = _FakeConnector(
        {
            "oversized/catalog-info.yaml": oversized,
            "ok/catalog-info.yaml": _system_manifest("survives-the-oversized-sibling"),
        }
    )

    _ingest_repository(connector, repo)

    assert (
        get_catalog_entity_model()
        .objects.filter(kind=KIND_SYSTEM, name="survives-the-oversized-sibling")
        .exists()
    )
    issue = IngestionIssue.objects.get(is_active=True)
    assert issue.path == "oversized/catalog-info.yaml"
    assert "maximum" in issue.message.lower()


def test_oversized_include_fragment_is_rejected(repo, group, monkeypatch):
    _patch_limits(monkeypatch, max_fetched_file_bytes=500)

    top = b"""
kind: Include
spec:
  paths: [.manifests/oversized.yaml]
---
apiVersion: atlas/v1alpha1
kind: System
metadata:
  name: sibling-survives-oversized-fragment
spec:
  owner: group:platform
"""
    connector = _FakeConnector(
        {
            "catalog-info.yaml": top,
            ".manifests/oversized.yaml": b"kind: System\n" * 100,
        }
    )

    _ingest_repository(connector, repo)

    assert (
        get_catalog_entity_model()
        .objects.filter(kind=KIND_SYSTEM, name="sibling-survives-oversized-fragment")
        .exists()
    )
    issue = IngestionIssue.objects.get(is_active=True)
    assert "maximum" in issue.message.lower()


def test_excessively_nested_yaml_is_rejected(repo, group, monkeypatch):
    _patch_limits(monkeypatch, max_yaml_nesting_depth=3)

    deeply_nested = b"[[[[[1]]]]]\n"  # nests well past a depth of 3
    connector = _FakeConnector(
        {
            "deep/catalog-info.yaml": deeply_nested,
            "ok/catalog-info.yaml": _system_manifest("survives-the-deep-sibling"),
        }
    )

    _ingest_repository(connector, repo)

    assert (
        get_catalog_entity_model()
        .objects.filter(kind=KIND_SYSTEM, name="survives-the-deep-sibling")
        .exists()
    )
    issue = IngestionIssue.objects.get(is_active=True)
    assert issue.path == "deep/catalog-info.yaml"


def test_include_depth_limit_is_rejected_without_a_cycle(repo, group, monkeypatch):
    _patch_limits(monkeypatch, max_include_depth=2)

    top = b"kind: Include\nspec:\n  paths: [.manifests/a.yaml]\n"
    a = b"kind: Include\nspec:\n  paths: [b.yaml]\n"
    b = (
        b"kind: Include\nspec:\n  paths: [c.yaml]\n---\n"
        + _system_manifest("depth-two-fragment")
    )
    c = _system_manifest("depth-three-fragment-never-ingested")
    connector = _FakeConnector(
        {
            "catalog-info.yaml": top,
            ".manifests/a.yaml": a,
            ".manifests/b.yaml": b,
            ".manifests/c.yaml": c,
        }
    )

    _ingest_repository(connector, repo)

    entities = get_catalog_entity_model().objects
    assert entities.filter(kind=KIND_SYSTEM, name="depth-two-fragment").exists()
    assert not entities.filter(
        kind=KIND_SYSTEM, name="depth-three-fragment-never-ingested"
    ).exists()
    issue = IngestionIssue.objects.get(is_active=True)
    assert "depth" in issue.message.lower()


def test_total_included_files_limit_is_rejected(repo, group, monkeypatch):
    _patch_limits(monkeypatch, max_included_files=2)

    top = b"kind: Include\nspec:\n  paths: [.manifests/*.yaml]\n"
    connector = _FakeConnector(
        {
            "catalog-info.yaml": top,
            ".manifests/a-catalog-info.yaml": _system_manifest("fragment-a"),
            ".manifests/b-catalog-info.yaml": _system_manifest("fragment-b"),
            ".manifests/c-catalog-info.yaml": _system_manifest("fragment-c"),
        }
    )

    _ingest_repository(connector, repo)

    entities = get_catalog_entity_model().objects
    assert entities.filter(kind=KIND_SYSTEM, name="fragment-a").exists()
    assert entities.filter(kind=KIND_SYSTEM, name="fragment-b").exists()
    assert not entities.filter(kind=KIND_SYSTEM, name="fragment-c").exists()
    issue = IngestionIssue.objects.get(is_active=True)
    assert "total" in issue.message.lower() or "maximum" in issue.message.lower()
