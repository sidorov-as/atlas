"""`IngestionIssue` lifecycle (manifest-processing
failures are persisted and admin-visible / an IngestionIssue is
self-clearing).

Exercises `_ingest_repository` across multiple runs against the three
existing silent failure sites it was extended to route through
`IngestionIssue` (connector fetch failure, YAML parse failure, manifest
schema-validation failure), no network involved.
"""

import pytest
from atlas_plugin_api import KIND_SYSTEM, get_catalog_entity_model

from atlas_plugin_ingestion.models import IngestionIssue
from atlas_plugin_ingestion.pipeline import _ingest_repository

pytestmark = pytest.mark.django_db

VALID_MANIFEST = b"""
apiVersion: atlas/v1alpha1
kind: System
metadata:
  name: user-management
spec:
  owner: group:platform
"""

INVALID_YAML = b'kind: ["unclosed'

INVALID_MANIFEST = b"""
apiVersion: atlas/v1alpha1
kind: System
metadata:
  name: broken-system
spec: {}
"""

MANIFEST_PATH = "catalog-info.yaml"


class _FakeConnector:
    """Serves fixed content for one repo, no network calls. `fail_fetch`
    names paths whose `fetch_file` raises instead of returning content."""

    def __init__(
        self, files: dict[str, bytes], fail_fetch: frozenset[str] = frozenset()
    ):
        self._files = files
        self._fail_fetch = fail_fetch

    def get_head_sha(self, repo):
        return "sha"

    def list_manifest_paths(self, repo):
        return list(self._files)

    def list_paths(self, repo):
        return list(self._files)

    def fetch_file(self, repo, path, sha):
        if path in self._fail_fetch:
            raise ConnectionError("boom")
        return self._files[path]


def test_fetch_failure_creates_an_issue(repo):
    connector = _FakeConnector(
        {MANIFEST_PATH: b""}, fail_fetch=frozenset({MANIFEST_PATH})
    )

    _ingest_repository(connector, repo)

    issue = IngestionIssue.objects.get(repository=repo, path=MANIFEST_PATH)
    assert issue.is_active is True
    assert MANIFEST_PATH in issue.message


def test_parse_failure_creates_an_issue(repo):
    connector = _FakeConnector({MANIFEST_PATH: INVALID_YAML})

    _ingest_repository(connector, repo)

    issue = IngestionIssue.objects.get(repository=repo, path=MANIFEST_PATH)
    assert issue.is_active is True
    assert MANIFEST_PATH in issue.message


def test_validation_failure_creates_an_issue(repo, group):
    connector = _FakeConnector({MANIFEST_PATH: INVALID_MANIFEST})

    _ingest_repository(connector, repo)

    issue = IngestionIssue.objects.get(repository=repo, path=MANIFEST_PATH)
    assert issue.is_active is True
    assert "invalid manifest document" in issue.message.lower()


def test_recurring_failure_updates_the_existing_issue_without_duplicating(repo):
    parse_failing = _FakeConnector({MANIFEST_PATH: INVALID_YAML})
    _ingest_repository(parse_failing, repo)
    first = IngestionIssue.objects.get(repository=repo, path=MANIFEST_PATH)

    fetch_failing = _FakeConnector(
        {MANIFEST_PATH: b""}, fail_fetch=frozenset({MANIFEST_PATH})
    )
    _ingest_repository(fetch_failing, repo)
    _ingest_repository(fetch_failing, repo)

    assert (
        IngestionIssue.objects.filter(repository=repo, path=MANIFEST_PATH).count() == 1
    )
    second = IngestionIssue.objects.get(repository=repo, path=MANIFEST_PATH)
    assert second.id == first.id
    assert second.first_seen == first.first_seen
    assert second.last_seen >= first.last_seen
    assert second.message != first.message
    assert "Failed to fetch" in second.message


def test_fixed_manifest_clears_the_prior_issue_without_deleting_it(repo, group):
    broken = _FakeConnector({MANIFEST_PATH: INVALID_MANIFEST})
    _ingest_repository(broken, repo)
    issue = IngestionIssue.objects.get(repository=repo, path=MANIFEST_PATH)
    assert issue.is_active is True

    fixed = _FakeConnector({MANIFEST_PATH: VALID_MANIFEST})
    _ingest_repository(fixed, repo)

    issue.refresh_from_db()
    assert issue.is_active is False
    assert (
        IngestionIssue.objects.filter(repository=repo, path=MANIFEST_PATH).count() == 1
    )
    assert (
        get_catalog_entity_model()
        .objects.filter(kind=KIND_SYSTEM, name="user-management")
        .exists()
    )
