"""Query path: engine candidates -> per-source `resolve` -> authorized hits.

Results are built only from `SearchSource.resolve` output, never from the
index: the index may be stale and knows nothing about who may read what.
Counts are derived from resolved hits only, so they cannot reveal documents
the actor may not see.
"""

import logging
from collections import Counter
from collections.abc import Collection, Sequence
from dataclasses import dataclass

from atlas_plugin_api import (
    SearchCandidate,
    SearchHit,
    SearchSource,
    get_search_source_lookup,
    split_document_id,
)

from . import runtime
from .snippets import Snippet, build_snippet, highlight_snippet

logger = logging.getLogger(__name__)

MAX_PAGE_SIZE = 50
MAX_CANDIDATES = 1000
"""Upper bound on candidates examined for one request."""


class SearchUnavailableError(RuntimeError):
    """The engine could not answer."""


@dataclass(frozen=True, slots=True)
class SearchResult:
    id: str
    kind: str
    kind_label: str
    title: str
    link: str
    snippet: Snippet | None


@dataclass(frozen=True, slots=True)
class KindCount:
    kind: str
    kind_label: str
    count: int


@dataclass(frozen=True, slots=True)
class SearchPage:
    results: list[SearchResult]
    total: int
    """Authorized hits seen while filling the page: exact when `has_more` is
    false, a lower bound otherwise."""
    page: int
    page_size: int
    has_more: bool
    facets: list[KindCount] | None = None
    """Authorized hits per kind for the whole query, ignoring the `kinds`
    filter, so a client can offer to narrow or widen it. Only set when
    requested; a lower bound when the query matched more than
    `MAX_CANDIDATES` documents."""


def kind_label(source: SearchSource, kind: str) -> str:
    """Display label of a kind: the source's own, else derived from the id."""
    labels = getattr(source, "kind_labels", None)
    if labels and kind in labels:
        return str(labels[kind])
    return kind.replace("_", " ").replace("-", " ").capitalize()


def _known_kinds(requested: Collection[str] | None) -> list[str] | None:
    """Kinds to filter by, or `None` for no filter; `[]` when nothing matches."""
    if not requested:
        return None
    registered = get_search_source_lookup()
    return [kind for kind in dict.fromkeys(requested) if registered.for_kind(kind)]


def _resolve(
    candidates: Sequence[SearchCandidate], actor: object
) -> dict[str, tuple[SearchHit, SearchSource]]:
    lookup = get_search_source_lookup()
    ids_by_source: dict[str, list[str]] = {}
    for candidate in candidates:
        kind, _ = split_document_id(candidate.id)
        source = lookup.for_kind(kind)
        if source is not None:
            ids_by_source.setdefault(source.id, []).append(candidate.id)
    resolved: dict[str, tuple[SearchHit, SearchSource]] = {}
    for source_id, ids in ids_by_source.items():
        source = lookup.get(source_id)
        wanted = set(ids)
        try:
            hits = source.resolve(ids, actor)
        except Exception:
            # One broken source must not take the whole search down.
            logger.exception("Search source %s failed to resolve hits", source_id)
            continue
        for hit in hits:
            if hit.id in wanted:
                resolved[hit.id] = (hit, source)
    return resolved


def search(
    actor: object,
    query: str,
    *,
    kinds: Collection[str] | None = None,
    page: int = 1,
    page_size: int = 20,
    with_facets: bool = False,
) -> SearchPage:
    """Authorized, ranked results for `query`.

    With `with_facets` every candidate is resolved (up to `MAX_CANDIDATES`)
    rather than just enough to fill the page, so that per-kind counts are
    complete; the `kinds` filter is then applied to the resolved hits.

    Raises `SearchUnavailableError` when the engine fails. A query shorter
    than the configured minimum yields an empty page without querying the
    engine.
    """
    config = runtime.get_config()
    engine = runtime.get_engine()
    text = query.strip()
    page_size = max(1, min(page_size, MAX_PAGE_SIZE))
    page = max(1, page)
    empty = SearchPage([], 0, page, page_size, False)
    if len(text) < config.min_query_length:
        return empty
    kind_filter = _known_kinds(kinds)
    if kind_filter == []:
        return empty

    # One extra tells whether a next page exists; facets need every candidate.
    wanted = MAX_CANDIDATES + 1 if with_facets else page * page_size + 1
    engine_kinds = None if with_facets else kind_filter
    chunk = max(page_size * 2, 50)
    collected: list[tuple[SearchCandidate, SearchHit, SearchSource]] = []
    offset = 0
    exhausted = False
    while len(collected) < wanted and offset < MAX_CANDIDATES:
        try:
            candidates = engine.query(
                text, kinds=engine_kinds, limit=chunk, offset=offset
            )
        except Exception as exc:
            logger.exception("Search engine query failed")
            raise SearchUnavailableError(str(exc)) from exc
        offset += chunk
        resolved = _resolve(candidates, actor)
        for candidate in candidates:
            found = resolved.get(candidate.id)
            if found is not None:
                collected.append((candidate, *found))
        if len(candidates) < chunk:
            exhausted = True
            break

    facets = None
    if with_facets:
        counts = Counter(hit.kind for _, hit, _ in collected)
        labels = {
            hit.kind: kind_label(source, hit.kind) for _, hit, source in collected
        }
        facets = sorted(
            (KindCount(kind, labels[kind], count) for kind, count in counts.items()),
            key=lambda facet: (-facet.count, facet.kind_label),
        )
        if kind_filter is not None:
            collected = [item for item in collected if item[1].kind in kind_filter]

    start = (page - 1) * page_size
    use_highlights = engine.capabilities.highlights
    results = []
    for candidate, hit, source in collected[start : start + page_size]:
        snippet = None
        if use_highlights and candidate.highlight:
            snippet = highlight_snippet(
                candidate.highlight, text, candidate.highlight_matches
            )
        if snippet is None:
            snippet = build_snippet(hit.text, hit.summary, text)
        results.append(
            SearchResult(
                id=hit.id,
                kind=hit.kind,
                kind_label=kind_label(source, hit.kind),
                title=hit.title,
                link=hit.link,
                snippet=snippet,
            )
        )
    return SearchPage(
        results=results,
        total=(
            len(collected)
            if exhausted or with_facets
            else min(len(collected), wanted - 1)
        ),
        page=page,
        page_size=page_size,
        has_more=len(collected) > start + page_size,
        facets=facets,
    )
