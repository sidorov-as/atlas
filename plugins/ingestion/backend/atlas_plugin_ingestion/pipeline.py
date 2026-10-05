"""Ingestion run orchestration.

One pass: for every registered repository, discover `**/catalog-info.yaml`
files, and upsert each document they contain. Failure is isolated at every
level narrower than "the whole run" — one repo, one file, or one document
failing is logged and skipped without affecting the others (per-manifest
failure isolation).

Within one repository, every `(kind, namespace, name)` ref its manifests would
emit is collected — from a cheap peek at the raw document, not full schema
validation — before any of them is upserted, so two manifests declaring the
same ref are both rejected as a duplicate rather than resolved by whichever
upserts last. Surviving documents are then
validated and upserted one at a time, in their original order, same as
before — so a document later in the same run can still reference an entity
created by one earlier in it (e.g. a Component after its System in one file).

Once every document has been upserted, a second pass reconciles each
successfully-upserted entity's declared `spec.relationships` into YAML-origin
Architecture Relationships — deferred to this second
pass so a declared target defined later in the same manifest is resolvable
regardless of document order.
"""

import logging
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

from atlas_plugin_api import CatalogEntity, refs
from atlas_plugin_apis.extension_points import due_for_spec_refresh

from . import limits as limits_module
from .connectors.base import MANIFEST_FILENAME, SourceConnector
from .database_schema import reconcile_database_schema
from .extension_points import connectors, parsers
from .issues import _record_issue, _resolve_issue
from .limits import FetchedFileTooLargeError, IngestionLimits
from .models import RegisteredRepository
from .parsing import PARSER_ID, YamlDocumentTooComplexError
from .paths import resolve_repository_relative_entry
from .upsert import (
    ClaimRejected,
    reconcile_claimed_entities,
    reconcile_declared_relationships,
    upsert_entity,
)
from .validation import (
    ManifestDocument,
    ManifestError,
    validate_manifest_document,
)

logger = logging.getLogger("atlas_plugin_ingestion")

RawEntry = tuple[str, Any]
UpsertedEntry = tuple[ManifestDocument, CatalogEntity]


@dataclass
class _IncludeBudget:
    """Mutable, shared-by-reference state for one repository's `Include`
    expansion (the maximum `Include`
    recursion depth and the maximum total number of files included in a
    single ingestion run). `included_count` accumulates across every
    branch of the expansion tree, unlike `visited` (per-chain, for cycle
    detection) — a mutable dataclass instance threaded through the
    recursion, rather than a return value, so sibling branches see each
    other's fetches."""

    max_depth: int
    max_files: int
    included_count: int = 0


def run_ingestion_pass() -> None:
    for repo in RegisteredRepository.objects.all():
        factory = connectors.resolve(repo.source_id)
        if factory is None:
            logger.error(
                "Skipping repository %s: no connector registered for source_id %r "
                "(no matching source in atlas.ingestion plugin config)",
                repo,
                repo.source_id,
            )
            continue
        try:
            with factory() as connector:
                _ingest_repository(connector, repo)
        except Exception:
            logger.exception("Ingestion run failed for repository %s", repo)


def refresh_spec_urls() -> None:
    """Re-fetch `spec_url` for every API with `spec_source='url'`.

    This plugin's own periodic job (`SPEC_REFRESH_JOB_ID`, registered by `plugin.register_jobs`) —
    the actual ORM query, fetch, and save live in `atlas_plugin_apis.
    extension_points.due_for_spec_refresh()`, since `atlas_plugin_apis` owns `ApiDetails`;
    this function just calls it on this plugin's own schedule.
    """
    due_for_spec_refresh()


def _ingest_repository(connector: SourceConnector, repo: RegisteredRepository) -> None:
    sha = connector.get_head_sha(repo)
    entries: list[RawEntry] = []
    attempted_paths: set[str] = set()
    failed_paths: set[str] = set()
    resolved_limits = limits_module.resolved_limits()
    budget = _IncludeBudget(
        max_depth=resolved_limits.max_include_depth,
        max_files=resolved_limits.max_included_files,
    )
    for path in connector.list_manifest_paths(repo):
        attempted_paths.add(path)
        try:
            content = connector.fetch_file(repo, path, sha)
            limits_module.check_fetched_file_size(content, resolved_limits)
        except FetchedFileTooLargeError as exc:
            message = f"{path} exceeds the configured maximum fetched-file size ({repo}): {exc}"
            logger.warning(message)
            _record_issue(repo, path, message)
            failed_paths.add(path)
            continue
        except Exception:
            logger.exception("Failed to fetch %s from %s", path, repo)
            _record_issue(repo, path, f"Failed to fetch {path} from {repo}")
            failed_paths.add(path)
            continue
        raw_entries = _parse(repo, path, content, failed_paths, resolved_limits)
        entries.extend(
            _expand_includes(
                connector,
                repo,
                sha,
                raw_entries,
                frozenset({path}),
                attempted_paths,
                failed_paths,
                budget,
                depth=0,
            )
        )

    upserted: list[UpsertedEntry] = []
    upserted_documents: list[tuple[str, Any, CatalogEntity]] = []
    for path, raw_document in _drop_duplicate_refs(repo, entries):
        result = _validate_and_upsert(repo, path, raw_document, failed_paths)
        if result is not None:
            upserted.append(result)
            document, instance = result
            upserted_documents.append((path, raw_document, instance))

    for document, instance in upserted:
        reconcile_declared_relationships(document, instance)
    for path, raw_document, instance in upserted_documents:
        reconcile_database_schema(
            connector, repo, sha, path, raw_document, instance, failed_paths
        )
    reconcile_claimed_entities(repo, upserted)

    for path in attempted_paths - failed_paths:
        _resolve_issue(repo, path)


def _parse(
    repo: RegisteredRepository,
    path: str,
    content: bytes,
    failed_paths: set[str],
    resolved_limits: IngestionLimits,
) -> list[RawEntry]:
    parser = parsers.resolve(PARSER_ID)
    try:
        raw_documents = parser.parse(
            content, max_nesting_depth=resolved_limits.max_yaml_nesting_depth
        )
    except YamlDocumentTooComplexError as exc:
        message = f"{path} is too complex to parse ({repo}): {exc}"
        logger.warning(message)
        _record_issue(repo, path, message)
        failed_paths.add(path)
        return []
    except Exception:
        logger.exception("Failed to parse %s from %s", path, repo)
        _record_issue(repo, path, f"Failed to parse {path} from {repo}")
        failed_paths.add(path)
        return []
    return [(path, raw_document) for raw_document in raw_documents]


INCLUDE_KIND = "Include"
"""`kind` marking a raw document as manifest composition rather than an
entity (`kind: Include` composes
additional manifest fragments)."""


def _is_include_document(raw_document: Any) -> bool:
    return isinstance(raw_document, dict) and raw_document.get("kind") == INCLUDE_KIND


def _expand_includes(
    connector: SourceConnector,
    repo: RegisteredRepository,
    sha: str,
    raw_entries: list[RawEntry],
    visited: frozenset[str],
    attempted_paths: set[str],
    failed_paths: set[str],
    budget: _IncludeBudget,
    depth: int,
) -> list[RawEntry]:
    """Replace every `kind: Include` document in `raw_entries` with the raw
    documents its `spec.paths` resolve to (recursively), so an `Include`
    document itself never reaches duplicate-ref detection or schema
    validation.

    `visited` is the set of repository-relative paths already in the current
    resolution chain (starting with the file `raw_entries` came from), used
    to detect and reject cycles (D4) rather than recursing forever. `depth`
    is that chain's current length, checked against `budget.max_depth`
    before a fragment one level deeper is fetched (`_include_fragment`);
    `budget.included_count` is checked and incremented there too, shared
    across every branch of the whole repository's expansion (unlike
    `visited`, which is per-chain).
    """
    expanded: list[RawEntry] = []
    for path, raw_document in raw_entries:
        if not _is_include_document(raw_document):
            expanded.append((path, raw_document))
            continue
        expanded.extend(
            _resolve_include(
                connector,
                repo,
                sha,
                path,
                raw_document,
                visited,
                attempted_paths,
                failed_paths,
                budget,
                depth,
            )
        )
    return expanded


def _resolve_include(
    connector: SourceConnector,
    repo: RegisteredRepository,
    sha: str,
    declaring_path: str,
    raw_document: Any,
    visited: frozenset[str],
    attempted_paths: set[str],
    failed_paths: set[str],
    budget: _IncludeBudget,
    depth: int,
) -> list[RawEntry]:
    spec = raw_document.get("spec")
    path_entries = spec.get("paths") if isinstance(spec, dict) else None
    if not isinstance(path_entries, list) or not path_entries:
        message = f"Include document in {declaring_path} has no spec.paths list"
        logger.warning("%s (%s)", message, repo)
        _record_issue(repo, declaring_path, message)
        failed_paths.add(declaring_path)
        return []

    base_dir = PurePosixPath(declaring_path).parent
    resolved: list[RawEntry] = []
    for entry in path_entries:
        if not isinstance(entry, str):
            message = (
                f"Include path entry {entry!r} in {declaring_path} is not a string"
            )
            logger.warning("%s (%s)", message, repo)
            _record_issue(repo, declaring_path, message)
            failed_paths.add(declaring_path)
            continue
        candidates = _resolve_include_entry(connector, repo, base_dir, entry)
        if candidates is None:
            message = (
                f"Include path {entry!r} in {declaring_path} is not a safe "
                "repository-relative path (absolute paths and '..' segments "
                "are rejected)"
            )
            logger.warning("%s (%s)", message, repo)
            _record_issue(repo, declaring_path, message)
            failed_paths.add(declaring_path)
            continue
        if not candidates:
            message = (
                f"Include path {entry!r} in {declaring_path} did not match any file"
            )
            logger.warning("%s (%s)", message, repo)
            _record_issue(repo, declaring_path, message)
            failed_paths.add(declaring_path)
            continue
        for candidate in candidates:
            resolved.extend(
                _include_fragment(
                    connector,
                    repo,
                    sha,
                    declaring_path,
                    candidate,
                    visited,
                    attempted_paths,
                    failed_paths,
                    budget,
                    depth,
                )
            )
    return resolved


def _resolve_include_entry(
    connector: SourceConnector,
    repo: RegisteredRepository,
    base_dir: PurePosixPath,
    entry: str,
) -> list[str] | None:
    """A single `spec.paths` entry resolved relative to `base_dir` — the
    directory of the file that declared the `Include` (ingestion-manifest-
    includes spec's "Include paths resolve relative to the including file's
    directory"). A glob entry (containing `*`, `?`, or `[`) is matched
    against every path the connector knows about; a plain entry resolves to
    exactly one path, whether or not it exists (existence is discovered by
    the fetch attempt in `_include_fragment`).

    Returns `None` — distinct from an empty list, which means "resolved to
    zero matches" — if a plain entry is rejected as unsafe (absolute,
    containing a `..` segment, or a NUL/control character)
    so the caller can report it as invalid
    rather than merely unmatched. `GitCheckout.read` independently
    re-verifies containment against the real checkout once one exists,
    catching what this pre-check cannot (a symlink that stays in-bounds
    syntactically but escapes on disk)."""
    if any(char in entry for char in "*?["):
        return _glob_paths(connector.list_paths(repo), base_dir, entry)
    resolved = resolve_repository_relative_entry(base_dir, entry)
    return None if resolved is None else [resolved]


def _glob_paths(
    all_paths: list[str], base_dir: PurePosixPath, pattern: str
) -> list[str]:
    """Every one of `all_paths` under `base_dir` whose path (relative to
    `base_dir`) matches `pattern` component-for-component — deliberately not
    using `PurePosixPath.match`'s right-aligned suffix matching, which would
    let a short pattern like `*.yaml` also match a deeper nested file it was
    never meant to reach."""
    pattern_depth = len(PurePosixPath(pattern).parts)
    matches = []
    for candidate in all_paths:
        try:
            relative = PurePosixPath(candidate).relative_to(base_dir)
        except ValueError:
            continue
        if len(relative.parts) == pattern_depth and relative.match(pattern):
            matches.append(candidate)
    return sorted(matches)


def _include_fragment(
    connector: SourceConnector,
    repo: RegisteredRepository,
    sha: str,
    declaring_path: str,
    resolved_path: str,
    visited: frozenset[str],
    attempted_paths: set[str],
    failed_paths: set[str],
    budget: _IncludeBudget,
    depth: int,
) -> list[RawEntry]:
    if PurePosixPath(resolved_path).name == MANIFEST_FILENAME:
        message = (
            f"Include path {resolved_path!r} in {declaring_path} is named "
            f"{MANIFEST_FILENAME!r} and would be ingested a second time by manifest discovery"
        )
        logger.warning("%s (%s)", message, repo)
        _record_issue(repo, declaring_path, message)
        failed_paths.add(declaring_path)
        return []
    if resolved_path in visited:
        message = (
            f"Include cycle detected: {resolved_path!r} (included from {declaring_path}) "
            "is already in the current resolution chain"
        )
        logger.warning("%s (%s)", message, repo)
        _record_issue(repo, declaring_path, message)
        failed_paths.add(declaring_path)
        return []

    next_depth = depth + 1
    if next_depth > budget.max_depth:
        message = (
            f"Include path {resolved_path!r} in {declaring_path} exceeds the "
            f"configured maximum Include recursion depth of {budget.max_depth}"
        )
        logger.warning("%s (%s)", message, repo)
        _record_issue(repo, declaring_path, message)
        failed_paths.add(declaring_path)
        return []
    if budget.included_count >= budget.max_files:
        message = (
            f"Include path {resolved_path!r} in {declaring_path} exceeds the "
            f"configured maximum of {budget.max_files} total included files "
            "for this ingestion run"
        )
        logger.warning("%s (%s)", message, repo)
        _record_issue(repo, declaring_path, message)
        failed_paths.add(declaring_path)
        return []
    budget.included_count += 1

    resolved_limits = limits_module.resolved_limits()
    attempted_paths.add(resolved_path)
    try:
        content = connector.fetch_file(repo, resolved_path, sha)
        limits_module.check_fetched_file_size(content, resolved_limits)
    except FetchedFileTooLargeError as exc:
        message = (
            f"Included path {resolved_path!r} in {declaring_path} exceeds the "
            f"configured maximum fetched-file size ({repo}): {exc}"
        )
        logger.warning(message)
        _record_issue(repo, resolved_path, message)
        failed_paths.add(resolved_path)
        return []
    except Exception:
        logger.exception(
            "Failed to fetch included path %s from %s", resolved_path, repo
        )
        _record_issue(
            repo,
            resolved_path,
            f"Failed to fetch included path {resolved_path} from {repo}",
        )
        failed_paths.add(resolved_path)
        return []

    fragment_entries = _parse(
        repo, resolved_path, content, failed_paths, resolved_limits
    )
    return _expand_includes(
        connector,
        repo,
        sha,
        fragment_entries,
        visited | {resolved_path},
        attempted_paths,
        failed_paths,
        budget,
        next_depth,
    )


def _manifest_ref(raw_document: Any) -> tuple[str, str, str] | None:
    """A cheap, validation-free peek at a raw document's `(kind, namespace, name)`.

    Used only to detect duplicate refs before any upsert runs — real schema
    validation (and the ref resolution it triggers) happens afterward, per
    document, so it can still see entities upserted earlier in the same run.
    """
    if not isinstance(raw_document, dict):
        return None
    kind = raw_document.get("kind")
    metadata = raw_document.get("metadata")
    name = metadata.get("name") if isinstance(metadata, dict) else None
    if not isinstance(kind, str) or not isinstance(name, str):
        return None
    return (kind.lower(), refs.DEFAULT_NAMESPACE, name)


def _drop_duplicate_refs(
    repo: RegisteredRepository, entries: list[RawEntry]
) -> list[RawEntry]:
    refs_seen = [_manifest_ref(raw_document) for _, raw_document in entries]
    counts: dict[tuple[str, str, str], int] = {}
    for ref in refs_seen:
        if ref is not None:
            counts[ref] = counts.get(ref, 0) + 1

    logged: set[tuple[str, str, str]] = set()
    unique = []
    for (path, raw_document), ref in zip(entries, refs_seen, strict=True):
        if ref is not None and counts[ref] > 1:
            if ref not in logged:
                logger.warning(
                    "Rejecting duplicate ref %s declared %d times in %s",
                    ref,
                    counts[ref],
                    repo,
                )
                logged.add(ref)
            continue
        unique.append((path, raw_document))
    return unique


def _validate_and_upsert(
    repo: RegisteredRepository,
    path: str,
    raw_document: Any,
    failed_paths: set[str],
) -> UpsertedEntry | None:
    try:
        document = validate_manifest_document(raw_document)
    except ManifestError as exc:
        logger.warning(
            "Skipping invalid manifest document in %s (%s): %s", path, repo, exc
        )
        _record_issue(
            repo, path, f"Skipping invalid manifest document in {path} ({repo}): {exc}"
        )
        failed_paths.add(path)
        return None

    try:
        instance = upsert_entity(document, repo)
    except refs.RefError as exc:
        logger.warning(
            "Skipping manifest document with an unresolved reference in %s (%s): %s",
            path,
            repo,
            exc,
        )
        return None
    except ClaimRejected as exc:
        logger.warning("Rejecting ingestion claim in %s (%s): %s", path, repo, exc)
        return None
    return document, instance


def _ingest_manifest(repo: RegisteredRepository, path: str, content: bytes) -> None:
    failed_paths: set[str] = set()
    entries = _parse(repo, path, content, failed_paths, limits_module.resolved_limits())
    upserted: list[UpsertedEntry] = []
    for doc_path, raw_document in _drop_duplicate_refs(repo, entries):
        result = _validate_and_upsert(repo, doc_path, raw_document, failed_paths)
        if result is not None:
            upserted.append(result)

    for document, instance in upserted:
        reconcile_declared_relationships(document, instance)
    reconcile_claimed_entities(repo, upserted)

    if path not in failed_paths:
        _resolve_issue(repo, path)
