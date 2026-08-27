"""Resource limits enforced at the ingestion fetch/parse boundary, not per capability.

A single `IngestionLimits` bundle is resolved once per independent fetch path
(`pipeline.py`'s manifest/`Include` resolution, `database_schema.py`'s
`sourceSqlPath` resolution — kept separate, mirroring
`paths.py`), rather than duplicating ad hoc constants in each. Every limit is
operator-configurable via `atlas.ingestion` plugin config
(`IngestionPluginConfig`) rather than hardcoded, so a real deployment isn't stuck if
it legitimately needs more; `resolved_limits()` falls back to the defaults
below when no config is bound (e.g. a unit test that never calls
`register_runtime`), mirroring `admin.py`'s own `LookupError` fallback.
"""

from dataclasses import dataclass

DEFAULT_MAX_FETCHED_FILE_BYTES = 5 * 1024 * 1024
"""5 MiB — generous relative to this repo's own example manifests/SQL
fixtures (order of a few KB), while still bounding worst-case memory use
from a hostile repository."""

DEFAULT_MAX_YAML_NESTING_DEPTH = 100
"""Real manifests nest a handful of levels deep; 100 comfortably covers any
legitimate document while still bounding a pathological one."""

DEFAULT_MAX_INCLUDE_DEPTH = 50
"""Maximum `kind: Include` chain length (building on the existing
cycle-detection requirement, which
catches infinite loops but not a large-but-finite chain)."""

DEFAULT_MAX_INCLUDED_FILES = 500
"""Maximum number of files fetched via `Include` resolution in a single
ingestion run (does not count top-level `catalog-info.yaml` discovery)."""


@dataclass(frozen=True)
class IngestionLimits:
    max_fetched_file_bytes: int = DEFAULT_MAX_FETCHED_FILE_BYTES
    max_yaml_nesting_depth: int = DEFAULT_MAX_YAML_NESTING_DEPTH
    max_include_depth: int = DEFAULT_MAX_INCLUDE_DEPTH
    max_included_files: int = DEFAULT_MAX_INCLUDED_FILES


class FetchedFileTooLargeError(Exception):
    """Raised by `check_fetched_file_size` when fetched content exceeds the
    configured maximum fetched-file size (content is bounded before parsing)."""


def check_fetched_file_size(content: bytes, limits: IngestionLimits) -> None:
    """Raise `FetchedFileTooLargeError` if `content` exceeds
    `limits.max_fetched_file_bytes` — called immediately after every
    `SourceConnector.fetch_file`, before the content is parsed or applied,
    regardless of which capability triggered the fetch (manifest discovery,
    `Include` fragment, or `sourceSqlPath`)."""
    if len(content) > limits.max_fetched_file_bytes:
        raise FetchedFileTooLargeError(
            f"fetched content is {len(content)} bytes, exceeding the "
            f"configured maximum of {limits.max_fetched_file_bytes} bytes",
        )


def resolved_limits() -> IngestionLimits:
    """The currently-configured `IngestionLimits`, from `atlas.ingestion`
    plugin config when bound, or `IngestionLimits()`'s defaults otherwise."""
    from atlas_plugin_api import get_plugin_config

    from .config import IngestionPluginConfig
    from .plugin import PLUGIN

    try:
        config = get_plugin_config(PLUGIN.id, IngestionPluginConfig)
    except LookupError:
        return IngestionLimits()
    return IngestionLimits(
        max_fetched_file_bytes=config.max_fetched_file_bytes,
        max_yaml_nesting_depth=config.max_yaml_nesting_depth,
        max_include_depth=config.max_include_depth,
        max_included_files=config.max_included_files,
    )
