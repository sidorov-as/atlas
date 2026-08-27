"""Ingestion of a Resource's `DatabaseSchema` Facet from a manifest-declared
`spec.databaseSchema`.

`databaseSchema` is parsed here, directly from a Resource manifest document's
raw `spec`, as this plugin's own ingestion-only schema — it is
never merged into `ResourceSpecPatch` and never handed to `EntityService.
update` as part of the Resource's own spec patch, so a distribution's
Resource CRUD API can't be used to set it (`DatabaseSchemaController` is the
only manual write path, and D6 further restricts that once the Resource is
YAML-managed).

`sourceSqlPath` is resolved (relative to the declaring manifest's own
directory) and fetched by ingestion itself, via the same `SourceConnector.
fetch_file` manifest discovery already uses — deliberately a
separate, independent implementation from `pipeline.py`'s `Include.spec.
paths` resolution, even though both resolve a manifest-relative repository
path (deliberately not shared; revisit only if a third consumer
appears). The registered `atlas.ingestion.facet_writers.v1` implementation
only ever receives already-fetched `dialect`/`source_sql`
text, never a connector or a path.
"""

import logging
from pathlib import PurePosixPath
from typing import Any

from atlas_plugin_api import CamelModel, CatalogEntity
from pydantic import ValidationError

from . import limits as limits_module
from .connectors.base import SourceConnector
from .extension_points import facet_writers
from .issues import _record_issue
from .limits import FetchedFileTooLargeError
from .models import RegisteredRepository
from .paths import resolve_repository_relative_entry

logger = logging.getLogger("atlas_plugin_ingestion")

FACET_WRITER_KEY = "database-schema"
"""Key `atlas_plugin_database_schema.plugin.register_runtime()` registers
its facet-writer under."""

_RESOURCE_KIND = "Resource"


class DatabaseSchemaDeclaration(CamelModel):
    """`Resource.spec.databaseSchema`'s shape — this plugin's
    own manifest-facing schema, independent of `ResourceSpecPatch`."""

    dialect: str
    source_sql_path: str


_MISSING = object()


def _raw_declaration(raw_document: Any) -> Any:
    """`raw_document.spec.databaseSchema` verbatim, or the `_MISSING` sentinel
    if the key isn't present at all — kept distinct from "present but
    invalid" (`_parse_declaration`) so a malformed declaration isn't treated
    the same as "the manifest doesn't declare one" (which clears the Facet,
    `reconcile_database_schema`): a typo shouldn't destroy existing data."""
    spec = raw_document.get("spec")
    if not isinstance(spec, dict) or "databaseSchema" not in spec:
        return _MISSING
    return spec["databaseSchema"]


def _parse_declaration(
    raw_declaration: Any,
    repo: RegisteredRepository,
    path: str,
) -> DatabaseSchemaDeclaration | None:
    """`raw_declaration`, validated as a `DatabaseSchemaDeclaration`, or
    `None` if it's invalid.

    An invalid declaration (missing/malformed field) is treated like any
    other per-manifest problem (failure isolation):
    recorded as an `IngestionIssue` and skipped, without blocking the
    Resource's own already-completed upsert, and without touching its
    Facet either way (neither `apply` nor `clear` — this manifest's intent
    is unknown, so the existing Facet, if any, is left alone).
    """
    try:
        return DatabaseSchemaDeclaration.model_validate(raw_declaration)
    except ValidationError as exc:
        message = f"Invalid spec.databaseSchema in {path} ({repo}): {exc}"
        logger.warning(message)
        _record_issue(repo, path, message)
        return None


def _resolve_source_sql_path(declaring_path: str, source_sql_path: str) -> str | None:
    """`source_sql_path` resolved relative to the directory of the manifest
    (or included fragment) at `declaring_path` — kept
    independent of `pipeline.py`'s `Include`-path resolution on purpose.

    Returns `None` if `source_sql_path` is rejected as unsafe (absolute,
    containing a `..` segment, or a NUL/control character).
    `GitCheckout.read` independently
    re-verifies containment against the real checkout once one exists,
    catching what this pre-check cannot (a symlink that stays in-bounds
    syntactically but escapes on disk)."""
    base_dir = PurePosixPath(declaring_path).parent
    return resolve_repository_relative_entry(base_dir, source_sql_path)


def reconcile_database_schema(
    connector: SourceConnector,
    repo: RegisteredRepository,
    sha: str,
    path: str,
    raw_document: Any,
    instance: CatalogEntity,
    failed_paths: set[str],
) -> None:
    """Apply or clear `instance`'s `DatabaseSchema` Facet to match
    `raw_document`'s declared `spec.databaseSchema`, if any.

    Runs after `instance`'s own `EntityService`-mediated upsert, the same
    second-pass shape `upsert.reconcile_declared_relationships` already uses
    for Architecture Relationships. A no-op for any document that isn't a
    Resource, and for a Resource when no facet-writer is registered (the
    `atlas.database-schema` plugin isn't selected for this distribution)
    — no fetch is even attempted either way. A fetch failure,
    an invalid declaration, or a failure inside the facet-writer itself is
    isolated the same way other per-manifest failures already are: recorded
    as an `IngestionIssue` and added to `failed_paths` (so `pipeline.py`'s
    final `_resolve_issue` sweep over `attempted_paths - failed_paths`
    doesn't immediately clear it again), without blocking the rest of this
    Resource's own upsert or the rest of the run.
    """
    if not isinstance(raw_document, dict) or raw_document.get("kind") != _RESOURCE_KIND:
        return

    writer = facet_writers.resolve(FACET_WRITER_KEY)
    if writer is None:
        return

    raw_declaration = _raw_declaration(raw_document)
    if raw_declaration is _MISSING:
        try:
            writer.clear(instance)
        except Exception:
            logger.exception(
                "Failed to clear DatabaseSchema facet for %s", instance.ref
            )
            _record_issue(
                repo, path, f"Failed to clear DatabaseSchema facet for {instance.ref}"
            )
            failed_paths.add(path)
        return

    declaration = _parse_declaration(raw_declaration, repo, path)
    if declaration is None:
        failed_paths.add(path)
        return

    resolved_path = _resolve_source_sql_path(path, declaration.source_sql_path)
    if resolved_path is None:
        message = (
            f"sourceSqlPath {declaration.source_sql_path!r} declared in {path} is not "
            "a safe repository-relative path (absolute paths and '..' segments are "
            "rejected)"
        )
        logger.warning("%s (%s)", message, repo)
        _record_issue(repo, path, message)
        failed_paths.add(path)
        return

    resolved_limits = limits_module.resolved_limits()
    try:
        fetched = connector.fetch_file(repo, resolved_path, sha)
        limits_module.check_fetched_file_size(fetched, resolved_limits)
        source_sql = fetched.decode("utf-8")
    except FetchedFileTooLargeError as exc:
        message = (
            f"{resolved_path} (databaseSchema sourceSqlPath declared in {path}) "
            f"exceeds the configured maximum fetched-file size ({repo}): {exc}"
        )
        logger.warning(message)
        _record_issue(repo, path, message)
        failed_paths.add(path)
        return
    except Exception:
        logger.exception(
            "Failed to fetch %s (databaseSchema sourceSqlPath declared in %s) from %s",
            resolved_path,
            path,
            repo,
        )
        _record_issue(
            repo,
            path,
            f"Failed to fetch {resolved_path} (databaseSchema sourceSqlPath) from {repo}",
        )
        failed_paths.add(path)
        return

    try:
        writer.apply(instance, declaration.dialect, source_sql)
    except Exception:
        logger.exception("Failed to apply DatabaseSchema facet for %s", instance.ref)
        _record_issue(
            repo, path, f"Failed to apply DatabaseSchema facet for {instance.ref}"
        )
        failed_paths.add(path)
