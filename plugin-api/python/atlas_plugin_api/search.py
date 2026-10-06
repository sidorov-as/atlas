"""Engine-neutral search contract (``add-search-core``).

Three seams, each replaceable on its own: *sources* (a data-owning plugin says
what is searchable, how to load it and who may see it), *engines* (where the
index lives and how matches are ranked) and the HTTP contract (owned by the
search plugin, not defined here).

This module is implementation-free: no Django models, no engine client
library. Sources and engines register through ``register_search_source`` /
``register_search_engine`` (same shape as ``register_authentication_provider``);
registering with no search plugin installed is harmless, nothing reads the
registries then.

The id of a document is ``<kind>:<key>``. It must be enough for the owning
source to re-load the live object: the index is never trusted for freshness
or permissions, results are built only from ``SearchSource.resolve``.
"""

from __future__ import annotations

import logging
from collections.abc import Collection, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)

DEFAULT_MAX_BODY_CHARS = 100_000
"""Default bound on ``SearchDocument.body`` (about 100 KB of text)."""

_max_body_chars = DEFAULT_MAX_BODY_CHARS


def configure_search_body_limit(max_chars: int | None) -> None:
    """Set the body bound (``None`` restores the default).

    Called by the consuming search plugin from its own configuration; the
    contract package itself reads no settings.
    """
    global _max_body_chars
    if max_chars is None:
        _max_body_chars = DEFAULT_MAX_BODY_CHARS
        return
    if max_chars < 1:
        raise ValueError("search body limit must be positive")
    _max_body_chars = max_chars


def get_search_body_limit() -> int:
    return _max_body_chars


def truncate_body(body: str, max_chars: int) -> str:
    """Truncate ``body`` to at most ``max_chars`` at a word boundary.

    A single word longer than the bound is cut mid-word, since there is no
    boundary to fall back to.
    """
    if len(body) <= max_chars:
        return body
    cut = body[:max_chars]
    if not body[max_chars].isspace():
        boundary = max((i for i, ch in enumerate(cut) if ch.isspace()), default=-1)
        if boundary > 0:
            cut = cut[:boundary]
    return cut.rstrip()


def _require_non_empty(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field_name} must be a non-empty, normalized string")
    return value


def split_document_id(document_id: str) -> tuple[str, str]:
    """Split ``<kind>:<key>`` into ``(kind, key)``."""
    kind, sep, key = document_id.partition(":")
    if not sep or not kind or not key:
        raise ValueError(f"search document id must be '<kind>:<key>': {document_id!r}")
    return kind, key


@dataclass(frozen=True, slots=True)
class SearchDocument:
    """One indexed unit: flat and self-describing.

    ``body`` is plain text and is bounded (see ``configure_search_body_limit``):
    longer text is truncated at a word boundary and a warning is logged. A
    source may truncate earlier. ``route`` is an opaque hint the source gets
    back through ``resolve`` to build the link; engines store it untouched.
    """

    id: str
    kind: str
    title: str
    body: str = ""
    summary: str | None = None
    route: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.kind, "search document kind")
        id_kind, _ = split_document_id(self.id)
        if id_kind != self.kind:
            raise ValueError(
                f"search document id {self.id!r} does not start with its kind "
                f"{self.kind!r}"
            )
        if not isinstance(self.title, str):
            raise TypeError("search document title must be a string")
        if not isinstance(self.body, str):
            raise TypeError("search document body must be a string")
        limit = _max_body_chars
        if len(self.body) > limit:
            logger.warning(
                "Search document %s body truncated from %d to at most %d characters",
                self.id,
                len(self.body),
                limit,
            )
            object.__setattr__(self, "body", truncate_body(self.body, limit))


@dataclass(frozen=True, slots=True)
class SearchCandidate:
    """An engine's answer for one match: id, score, optional highlight.

    ``highlight`` is plain text with no markup; only meaningful when the
    engine declares ``EngineCapabilities.highlights``.

    ``highlight_matches`` optionally locates what the engine matched inside
    ``highlight``: ordered, non-overlapping, non-empty ``[start, end)`` ranges
    counted in Unicode code points (Python string indexes) of ``highlight``.
    The highlight is final: the offsets are valid for it exactly as given, so
    a consumer must not clean or otherwise transform the text before using
    them. Without offsets the consumer locates the matches itself.
    """

    id: str
    score: float
    highlight: str | None = None
    highlight_matches: tuple[tuple[int, int], ...] = ()

    def __post_init__(self) -> None:
        split_document_id(self.id)
        if not self.highlight_matches:
            return
        if self.highlight is None:
            raise ValueError("search candidate has match offsets but no highlight")
        previous_end = 0
        for start, end in self.highlight_matches:
            if not 0 <= start < end <= len(self.highlight):
                raise ValueError(
                    f"search candidate match ({start}, {end}) is empty or outside "
                    f"the highlight of {len(self.highlight)} characters"
                )
            if start < previous_end:
                raise ValueError(
                    f"search candidate match ({start}, {end}) is unordered or "
                    "overlaps the previous one"
                )
            previous_end = end


@dataclass(frozen=True, slots=True)
class SearchHit:
    """A live, authorized result built by a source's ``resolve``.

    ``text`` is the plain text the snippet is generated from. ``link`` is an
    application-relative path.
    """

    id: str
    kind: str
    title: str
    link: str
    text: str = ""
    summary: str | None = None

    def __post_init__(self) -> None:
        id_kind, _ = split_document_id(self.id)
        if id_kind != self.kind:
            raise ValueError(
                f"search hit id {self.id!r} does not start with its kind {self.kind!r}"
            )
        _require_non_empty(self.link, "search hit link")


@dataclass(frozen=True, slots=True)
class EngineCapabilities:
    """Optional engine features the search plugin may rely on."""

    highlights: bool = False
    """Candidates carry ready-made highlights; core snippets are skipped."""

    typo_tolerance: bool = False
    """The engine matches words despite small spelling mistakes. Informational:
    the search plugin does not change behavior, status and docs can report it."""


@dataclass(frozen=True, slots=True)
class EngineHealth:
    ok: bool
    detail: str | None = None
    document_count: int | None = None
    """Indexed documents, when the engine can tell; lets the search plugin
    notice an empty index."""


@runtime_checkable
class SearchSource(Protocol):
    """Implemented by a plugin that owns searchable data."""

    @property
    def id(self) -> str: ...

    @property
    def kinds(self) -> Collection[str]:
        """Document kinds this source owns; unique across all sources."""
        ...

    @property
    def watched_models(self) -> Collection[str]:
        """Models (``app_label.ModelName``) whose changes affect documents."""
        ...

    def document_ids_for_instance(self, instance: Any) -> Iterable[str]:
        """Ids of the documents affected by a changed ``instance``.

        For a related model this is its owner's document id. A deleted
        object's id is returned too: ``documents`` then omits it and the
        indexer deletes it from the engine.
        """
        ...

    def documents(self, ids: Sequence[str]) -> Iterable[SearchDocument]:
        """Live documents for ``ids``; missing or ineligible ids are omitted."""
        ...

    def all_documents(self) -> Iterator[SearchDocument]:
        """Every document of this source, for a full rebuild."""
        ...

    def resolve(self, ids: Sequence[str], actor: Any) -> Sequence[SearchHit]:
        """Live hits for the ids ``actor`` may read.

        Inaccessible, deleted or unknown ids are omitted without error.
        """
        ...


@runtime_checkable
class SearchEngine(Protocol):
    """Implemented by an engine adapter plugin."""

    @property
    def id(self) -> str: ...

    @property
    def capabilities(self) -> EngineCapabilities: ...

    def upsert(self, documents: Iterable[SearchDocument]) -> None: ...

    def delete(self, ids: Iterable[str]) -> None: ...

    def replace_all(self, documents: Iterable[SearchDocument]) -> None:
        """Replace the whole index atomically from a stream of documents.

        If this fails partway, the previous content stays queryable.
        """
        ...

    def query(
        self,
        text: str,
        *,
        kinds: Collection[str] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Sequence[SearchCandidate]:
        """Candidates ordered by descending relevance."""
        ...

    def health(self) -> EngineHealth: ...


class InvalidSearchSourceError(TypeError):
    """A registered source or engine does not implement its protocol."""


class DuplicateSearchSourceError(ValueError):
    def __init__(
        self,
        what: str,
        value: str,
        *,
        existing_owner: str | None,
        new_owner: str | None,
    ) -> None:
        super().__init__(
            f"Search {what} {value!r} is already registered by "
            f"{existing_owner!r}; conflicting registration from {new_owner!r}"
        )
        self.what = what
        self.value = value
        self.existing_owner = existing_owner
        self.new_owner = new_owner


class DuplicateSearchEngineError(DuplicateSearchSourceError):
    pass


class DuplicateSearchDocumentError(ValueError):
    """Two sources produced the same document id."""

    def __init__(self, document_id: str, *, first_source: str, second_source: str):
        super().__init__(
            f"Search document id {document_id!r} is produced by both "
            f"{first_source!r} and {second_source!r}"
        )
        self.document_id = document_id
        self.first_source = first_source
        self.second_source = second_source


class SearchSourceRegistry:
    def __init__(self) -> None:
        self._sources: dict[str, SearchSource] = {}
        self._owners: dict[str, str | None] = {}
        self._kind_sources: dict[str, str] = {}

    def register(self, source: SearchSource, *, owner: str | None = None) -> None:
        if not isinstance(source, SearchSource):
            raise InvalidSearchSourceError(
                "search source does not implement the SearchSource protocol"
            )
        source_id = _require_non_empty(source.id, "search source id")
        kinds = tuple(source.kinds)
        if not kinds:
            raise InvalidSearchSourceError(
                f"search source {source_id!r} declares no kinds"
            )
        for kind in kinds:
            _require_non_empty(kind, "search source kind")
        if source_id in self._sources:
            raise DuplicateSearchSourceError(
                "source id",
                source_id,
                existing_owner=self._owners[source_id],
                new_owner=owner,
            )
        for kind in kinds:
            if kind in self._kind_sources:
                other = self._kind_sources[kind]
                raise DuplicateSearchSourceError(
                    "kind",
                    kind,
                    existing_owner=self._owners[other],
                    new_owner=owner,
                )
        self._sources[source_id] = source
        self._owners[source_id] = owner
        for kind in kinds:
            self._kind_sources[kind] = source_id

    def get(self, source_id: str) -> SearchSource | None:
        return self._sources.get(source_id)

    def all(self) -> tuple[SearchSource, ...]:
        return tuple(self._sources.values())

    def for_kind(self, kind: str) -> SearchSource | None:
        source_id = self._kind_sources.get(kind)
        return self._sources[source_id] if source_id is not None else None

    def kinds(self) -> Mapping[str, str]:
        """Mapping of kind to the id of the source that owns it."""
        return MappingProxyType(dict(self._kind_sources))


class SearchEngineRegistry:
    def __init__(self) -> None:
        self._engines: dict[str, SearchEngine] = {}
        self._owners: dict[str, str | None] = {}

    def register(self, engine: SearchEngine, *, owner: str | None = None) -> None:
        if not isinstance(engine, SearchEngine):
            raise InvalidSearchSourceError(
                "search engine does not implement the SearchEngine protocol"
            )
        if not isinstance(engine.capabilities, EngineCapabilities):
            raise InvalidSearchSourceError(
                "search engine capabilities must be EngineCapabilities"
            )
        engine_id = _require_non_empty(engine.id, "search engine id")
        if engine_id in self._engines:
            raise DuplicateSearchEngineError(
                "engine id",
                engine_id,
                existing_owner=self._owners[engine_id],
                new_owner=owner,
            )
        self._engines[engine_id] = engine
        self._owners[engine_id] = owner

    def get(self, engine_id: str) -> SearchEngine | None:
        return self._engines.get(engine_id)

    def all(self) -> tuple[SearchEngine, ...]:
        return tuple(self._engines.values())

    def owner_of(self, engine_id: str) -> str | None:
        return self._owners.get(engine_id)


class SearchEngineSelectionError(RuntimeError):
    """No usable engine could be chosen; the search plugin must not start."""


def select_search_engine(
    lookup: SearchEngineLookup,
    engine_setting: str | None = None,
) -> SearchEngine:
    """Choose the one engine the search plugin uses.

    ``engine_setting`` is the optional ``engine`` plugin setting: the id of the
    plugin that registered the engine to use. Without it exactly one engine
    must be registered. Every other case raises ``SearchEngineSelectionError``
    naming the engines found.
    """
    engines = lookup.all()
    registered = ", ".join(
        f"{engine.id!r} (owner {lookup.owner_of(engine.id)!r})" for engine in engines
    )
    if not engines:
        raise SearchEngineSelectionError(
            "Search requires an engine plugin, but no search engine is registered"
        )
    if engine_setting is None:
        if len(engines) == 1:
            return engines[0]
        raise SearchEngineSelectionError(
            f"Several search engines are registered: {registered}; "
            "set the search plugin's 'engine' setting to the plugin id of the "
            "one to use"
        )
    matching = [e for e in engines if lookup.owner_of(e.id) == engine_setting]
    if not matching:
        raise SearchEngineSelectionError(
            f"The search plugin's 'engine' setting names {engine_setting!r}, but "
            f"that plugin registered no search engine; registered: {registered}"
        )
    if len(matching) > 1:
        ids = ", ".join(repr(e.id) for e in matching)
        raise SearchEngineSelectionError(
            f"Plugin {engine_setting!r} registered several search engines "
            f"({ids}); the 'engine' setting cannot choose between them"
        )
    return matching[0]


@runtime_checkable
class SearchSourceLookup(Protocol):
    def get(self, source_id: str) -> SearchSource | None: ...

    def all(self) -> tuple[SearchSource, ...]: ...

    def for_kind(self, kind: str) -> SearchSource | None: ...


@runtime_checkable
class SearchEngineLookup(Protocol):
    def get(self, engine_id: str) -> SearchEngine | None: ...

    def all(self) -> tuple[SearchEngine, ...]: ...

    def owner_of(self, engine_id: str) -> str | None: ...


class _SourceReadView:
    __slots__ = ("__registry",)

    def __init__(self, registry: SearchSourceRegistry) -> None:
        self.__registry = registry

    def get(self, source_id: str) -> SearchSource | None:
        return self.__registry.get(source_id)

    def all(self) -> tuple[SearchSource, ...]:
        return self.__registry.all()

    def for_kind(self, kind: str) -> SearchSource | None:
        return self.__registry.for_kind(kind)


class _EngineReadView:
    __slots__ = ("__registry",)

    def __init__(self, registry: SearchEngineRegistry) -> None:
        self.__registry = registry

    def get(self, engine_id: str) -> SearchEngine | None:
        return self.__registry.get(engine_id)

    def all(self) -> tuple[SearchEngine, ...]:
        return self.__registry.all()

    def owner_of(self, engine_id: str) -> str | None:
        return self.__registry.owner_of(engine_id)


_search_source_registry = SearchSourceRegistry()
_search_engine_registry = SearchEngineRegistry()
_search_source_lookup = _SourceReadView(_search_source_registry)
_search_engine_lookup = _EngineReadView(_search_engine_registry)


def register_search_source(source: SearchSource, *, owner: str | None = None) -> None:
    """Register a source after Django setup (from ``register_runtime()``)."""
    _search_source_registry.register(source, owner=owner)


def register_search_engine(engine: SearchEngine, *, owner: str | None = None) -> None:
    """Register an engine after Django setup (from ``register_runtime()``)."""
    _search_engine_registry.register(engine, owner=owner)


def get_search_source_lookup() -> SearchSourceLookup:
    """Read-only view of registered sources, for the search plugin."""
    return _search_source_lookup


def get_search_engine_lookup() -> SearchEngineLookup:
    """Read-only view of registered engines, for the search plugin."""
    return _search_engine_lookup


__all__ = [
    "DEFAULT_MAX_BODY_CHARS",
    "DuplicateSearchDocumentError",
    "DuplicateSearchEngineError",
    "DuplicateSearchSourceError",
    "EngineCapabilities",
    "EngineHealth",
    "InvalidSearchSourceError",
    "SearchCandidate",
    "SearchDocument",
    "SearchEngine",
    "SearchEngineLookup",
    "SearchEngineRegistry",
    "SearchEngineSelectionError",
    "SearchHit",
    "SearchSource",
    "SearchSourceLookup",
    "SearchSourceRegistry",
    "configure_search_body_limit",
    "get_search_body_limit",
    "get_search_engine_lookup",
    "get_search_source_lookup",
    "register_search_engine",
    "register_search_source",
    "select_search_engine",
    "split_document_id",
    "truncate_body",
]
