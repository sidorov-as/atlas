"""Tests for `database_schema.py`: `sourceSqlPath`
resolution, fetch-failure isolation, and the two end-to-end shapes:
a declared schema populates the
Resource's `DatabaseSchema` Facet when `atlas.database-schema` is active
(6.4), and has no effect at all, without error, when it isn't (6.5).

6.4 deliberately runs against the *real* registered `atlas.ingestion.
facet_writers.v1` implementation (this test environment's own distribution
selects `atlas.database-schema` — `server.settings.selected_plugins`) rather
than a fake, since asserting the Facet was actually populated needs the real
one; only attribute access on `entity.database_schema` is used, never an
import of `atlas_plugin_database_schema` itself (forbidden plugin-to-plugin
edge, `test_import_boundaries.py`). 6.2's isolation tests and 6.5 swap in a
fake/empty registry instead, to control exactly what's registered.
"""

import pytest
from atlas_plugin_api import KIND_RESOURCE, get_catalog_entity_model
from django.core.exceptions import ObjectDoesNotExist

import atlas_plugin_ingestion.database_schema as database_schema_module
import atlas_plugin_ingestion.limits as limits_module
from atlas_plugin_ingestion.database_schema import _resolve_source_sql_path
from atlas_plugin_ingestion.extension_points import KeyedExtensionPoint
from atlas_plugin_ingestion.limits import IngestionLimits
from atlas_plugin_ingestion.models import IngestionIssue
from atlas_plugin_ingestion.pipeline import _ingest_repository

pytestmark = pytest.mark.django_db


def _resource_manifest(
    name: str, dialect: str = "postgresql", source_sql_path: str = "db/schema.sql"
) -> bytes:
    return f"""
apiVersion: atlas/v1alpha1
kind: Resource
metadata:
  name: {name}
spec:
  type: database
  owner: group:platform
  databaseSchema:
    dialect: {dialect}
    sourceSqlPath: {source_sql_path}
""".encode()


VALID_SQL = b"CREATE TABLE users (id uuid PRIMARY KEY, email varchar(255) NOT NULL);"


class _FakeConnector:
    def __init__(self, files: dict[str, bytes]):
        self._files = files

    def get_head_sha(self, repo):
        return "sha"

    def list_manifest_paths(self, repo):
        return [
            path
            for path in self._files
            if path.rsplit("/", 1)[-1] == "catalog-info.yaml"
        ]

    def list_paths(self, repo):
        return list(self._files)

    def fetch_file(self, repo, path, sha):
        return self._files[path]


class _FakeWriter:
    def __init__(self):
        self.applied: list[tuple] = []
        self.cleared: list = []
        self.apply_error: Exception | None = None
        self.clear_error: Exception | None = None

    def apply(self, entity, dialect, source_sql):
        if self.apply_error is not None:
            raise self.apply_error
        self.applied.append((entity, dialect, source_sql))

    def clear(self, entity):
        if self.clear_error is not None:
            raise self.clear_error
        self.cleared.append(entity)


def _register_fake_writer(monkeypatch, writer) -> None:
    fresh = KeyedExtensionPoint("atlas.ingestion.facet_writers.v1")
    fresh.register(database_schema_module.FACET_WRITER_KEY, writer)
    monkeypatch.setattr(database_schema_module, "facet_writers", fresh)


def _empty_registry(monkeypatch) -> None:
    monkeypatch.setattr(
        database_schema_module,
        "facet_writers",
        KeyedExtensionPoint("atlas.ingestion.facet_writers.v1"),
    )


# 6.2: sourceSqlPath resolution


def test_resolves_relative_to_the_declaring_manifests_own_directory():
    assert _resolve_source_sql_path(
        "services/payments/catalog-info.yaml", "db/schema.sql"
    ) == ("services/payments/db/schema.sql")


def test_resolves_relative_to_a_top_level_manifests_directory():
    assert (
        _resolve_source_sql_path("catalog-info.yaml", "db/schema.sql")
        == "db/schema.sql"
    )


def test_rejects_parent_segment_traversal():
    """A `..` segment used to pass through
    unnormalized (`services/payments/../shared/schema.sql`), which a
    connector's naive file read could walk outside the repository checkout
    with. It's now rejected instead of resolved."""
    assert (
        _resolve_source_sql_path(
            "services/payments/catalog-info.yaml", "../shared/schema.sql"
        )
        is None
    )


def test_rejects_absolute_source_sql_path():
    assert (
        _resolve_source_sql_path("services/payments/catalog-info.yaml", "/etc/passwd")
        is None
    )


# Unsafe `sourceSqlPath` values are
# rejected without blocking the Resource's own entity upsert. Symlink-escape
# coverage lives in `test_git_connector.py` instead — see
# `test_includes.py`'s equivalent note for why this pre-check can't catch it.


def test_absolute_source_sql_path_is_rejected_end_to_end(repo, group, monkeypatch):
    writer = _FakeWriter()
    _register_fake_writer(monkeypatch, writer)

    top = _resource_manifest("payments-db", source_sql_path="/etc/passwd")
    connector = _FakeConnector({"catalog-info.yaml": top})

    _ingest_repository(connector, repo)

    assert (
        get_catalog_entity_model()
        .objects.filter(kind=KIND_RESOURCE, name="payments-db")
        .exists()
    )
    assert writer.applied == []
    issue = IngestionIssue.objects.get(is_active=True)
    assert "/etc/passwd" in issue.message


def test_traversal_source_sql_path_is_rejected_end_to_end(repo, group, monkeypatch):
    writer = _FakeWriter()
    _register_fake_writer(monkeypatch, writer)

    top = _resource_manifest("payments-db", source_sql_path="../../etc/passwd")
    connector = _FakeConnector({"catalog-info.yaml": top})

    _ingest_repository(connector, repo)

    assert (
        get_catalog_entity_model()
        .objects.filter(kind=KIND_RESOURCE, name="payments-db")
        .exists()
    )
    assert writer.applied == []
    issue = IngestionIssue.objects.get(is_active=True)
    assert "../../etc/passwd" in issue.message


# An oversized sourceSqlPath file is
# rejected before it's applied to the facet, without blocking the Resource's
# own entity upsert (fetched content is bounded
# before parsing).


def test_oversized_source_sql_path_file_is_rejected(repo, group, monkeypatch):
    monkeypatch.setattr(
        limits_module,
        "resolved_limits",
        lambda: IngestionLimits(max_fetched_file_bytes=500),
    )
    writer = _FakeWriter()
    _register_fake_writer(monkeypatch, writer)

    top = _resource_manifest("payments-db")
    oversized_sql = VALID_SQL * 20  # well over the 500-byte limit
    connector = _FakeConnector(
        {"catalog-info.yaml": top, "db/schema.sql": oversized_sql}
    )

    _ingest_repository(connector, repo)

    assert (
        get_catalog_entity_model()
        .objects.filter(kind=KIND_RESOURCE, name="payments-db")
        .exists()
    )
    assert writer.applied == []
    issue = IngestionIssue.objects.get(is_active=True)
    assert "maximum" in issue.message.lower()


# 6.2: fetch-failure isolation (using a fake writer, so only the fetch step is exercised)


def test_fetch_failure_is_isolated_and_recorded_as_an_issue(repo, group, monkeypatch):
    writer = _FakeWriter()
    _register_fake_writer(monkeypatch, writer)

    top = _resource_manifest("payments-db")
    connector = _FakeConnector(
        {"catalog-info.yaml": top}
    )  # no 'db/schema.sql' entry: fetch raises KeyError

    _ingest_repository(connector, repo)

    assert (
        get_catalog_entity_model()
        .objects.filter(kind=KIND_RESOURCE, name="payments-db")
        .exists()
    )
    assert writer.applied == []
    issue = IngestionIssue.objects.get(is_active=True)
    assert "db/schema.sql" in issue.message


def test_a_fetch_failure_does_not_get_immediately_resolved_by_the_final_sweep(
    repo, group, monkeypatch
):
    """Regression coverage for the ordering hazard `reconcile_database_schema`
    guards against: `pipeline._ingest_repository`'s trailing `_resolve_issue`
    sweep runs over `attempted_paths - failed_paths`, so a facet-level
    failure must add its manifest's path to `failed_paths` or that sweep
    immediately clears the issue this test asserts stays active."""
    writer = _FakeWriter()
    _register_fake_writer(monkeypatch, writer)

    top = _resource_manifest("payments-db")
    connector = _FakeConnector({"catalog-info.yaml": top})

    _ingest_repository(connector, repo)

    assert IngestionIssue.objects.filter(
        path="catalog-info.yaml", is_active=True
    ).exists()


def test_invalid_declaration_is_isolated_and_recorded_as_an_issue(
    repo, group, monkeypatch
):
    writer = _FakeWriter()
    _register_fake_writer(monkeypatch, writer)

    top = b"""
apiVersion: atlas/v1alpha1
kind: Resource
metadata:
  name: payments-db
spec:
  type: database
  owner: group:platform
  databaseSchema:
    sourceSqlPath: db/schema.sql
"""  # missing required `dialect`
    connector = _FakeConnector({"catalog-info.yaml": top})

    _ingest_repository(connector, repo)

    assert (
        get_catalog_entity_model()
        .objects.filter(kind=KIND_RESOURCE, name="payments-db")
        .exists()
    )
    assert writer.applied == []
    assert writer.cleared == []
    issue = IngestionIssue.objects.get(is_active=True)
    assert "databaseSchema" in issue.message


def test_facet_writer_apply_failure_is_isolated(repo, group, monkeypatch):
    writer = _FakeWriter()
    writer.apply_error = RuntimeError("boom")
    _register_fake_writer(monkeypatch, writer)

    top = _resource_manifest("payments-db")
    connector = _FakeConnector({"catalog-info.yaml": top, "db/schema.sql": VALID_SQL})

    _ingest_repository(connector, repo)

    assert (
        get_catalog_entity_model()
        .objects.filter(kind=KIND_RESOURCE, name="payments-db")
        .exists()
    )
    issue = IngestionIssue.objects.get(is_active=True)
    assert "payments-db" in issue.message.lower() or "apply" in issue.message.lower()


def test_declaring_no_databaseschema_calls_clear_when_a_writer_is_registered(
    repo, group, monkeypatch
):
    writer = _FakeWriter()
    _register_fake_writer(monkeypatch, writer)

    top = b"""
apiVersion: atlas/v1alpha1
kind: Resource
metadata:
  name: payments-db
spec:
  type: database
  owner: group:platform
"""
    connector = _FakeConnector({"catalog-info.yaml": top})

    _ingest_repository(connector, repo)

    assert len(writer.cleared) == 1
    assert not IngestionIssue.objects.filter(is_active=True).exists()


def test_non_resource_kinds_never_resolve_a_facet_writer(repo, group, monkeypatch):
    writer = _FakeWriter()
    _register_fake_writer(monkeypatch, writer)

    top = b"""
apiVersion: atlas/v1alpha1
kind: System
metadata:
  name: payments
spec:
  owner: group:platform
"""
    connector = _FakeConnector({"catalog-info.yaml": top})

    _ingest_repository(connector, repo)

    assert writer.applied == []
    assert writer.cleared == []


# 6.4/6.5: end-to-end, through the real registered facet-writer


def test_a_declared_schema_populates_the_real_facet_after_a_run(repo, group):
    top = _resource_manifest("orders-db")
    connector = _FakeConnector({"catalog-info.yaml": top, "db/schema.sql": VALID_SQL})

    _ingest_repository(connector, repo)

    entity = get_catalog_entity_model().objects.get(
        kind=KIND_RESOURCE, name="orders-db"
    )
    facet = entity.database_schema
    assert facet.dialect == "postgresql"
    assert facet.source_sql == VALID_SQL.decode()
    assert facet.parsed_schema["tables"][0]["name"] == "users"
    assert not IngestionIssue.objects.filter(is_active=True).exists()


def test_reingestion_with_changed_content_updates_the_facet_in_place(repo, group):
    top = _resource_manifest("orders-db")
    connector = _FakeConnector({"catalog-info.yaml": top, "db/schema.sql": VALID_SQL})
    _ingest_repository(connector, repo)

    other_sql = b"CREATE TABLE accounts (id uuid PRIMARY KEY);"
    connector = _FakeConnector({"catalog-info.yaml": top, "db/schema.sql": other_sql})
    _ingest_repository(connector, repo)

    entity = get_catalog_entity_model().objects.get(
        kind=KIND_RESOURCE, name="orders-db"
    )
    assert entity.database_schema.source_sql == other_sql.decode()
    assert entity.database_schema.parsed_schema["tables"][0]["name"] == "accounts"


def test_dropping_the_declaration_clears_the_real_facet(repo, group):
    top = _resource_manifest("orders-db")
    connector = _FakeConnector({"catalog-info.yaml": top, "db/schema.sql": VALID_SQL})
    _ingest_repository(connector, repo)

    without_declaration = b"""
apiVersion: atlas/v1alpha1
kind: Resource
metadata:
  name: orders-db
spec:
  type: database
  owner: group:platform
"""
    connector = _FakeConnector({"catalog-info.yaml": without_declaration})
    _ingest_repository(connector, repo)

    entity = get_catalog_entity_model().objects.get(
        kind=KIND_RESOURCE, name="orders-db"
    )
    with pytest.raises(ObjectDoesNotExist):
        entity.database_schema  # noqa: B018


def test_no_effect_when_no_facet_writer_is_registered(repo, group, monkeypatch):
    """No effect when the plugin isn't
    active — simulates a distribution that doesn't select `atlas.database-
    schema` by swapping in an empty registry."""
    _empty_registry(monkeypatch)

    fetch_attempts = []

    class _TrackingConnector(_FakeConnector):
        def fetch_file(self, repo, path, sha):
            fetch_attempts.append(path)
            return super().fetch_file(repo, path, sha)

    top = _resource_manifest("inventory-db")
    connector = _TrackingConnector(
        {"catalog-info.yaml": top, "db/schema.sql": VALID_SQL}
    )

    _ingest_repository(connector, repo)

    assert (
        get_catalog_entity_model()
        .objects.filter(kind=KIND_RESOURCE, name="inventory-db")
        .exists()
    )
    assert "db/schema.sql" not in fetch_attempts
    assert not IngestionIssue.objects.filter(is_active=True).exists()
