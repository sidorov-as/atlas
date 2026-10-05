"""PostgreSQL full-text implementation of the `SearchEngine` contract."""

from collections.abc import Collection, Iterable, Iterator
from itertools import batched

from atlas_plugin_api import (
    EngineCapabilities,
    EngineHealth,
    SearchCandidate,
    SearchDocument,
)
from django.contrib.postgres.search import (
    SearchQuery,
    SearchRank,
    SearchVector,
)
from django.db import DatabaseError, transaction
from django.db.models import F, Value

from .config import DEFAULT_TEXT_SEARCH_CONFIG
from .models import SearchIndexEntry

BATCH_SIZE = 500

TITLE_WEIGHT = "A"
BODY_WEIGHT = "B"


class PostgresSearchEngine:
    """Keeps the index in the application's own PostgreSQL database."""

    id = "postgres"
    capabilities = EngineCapabilities(highlights=False)

    def __init__(self, text_search_config: str = DEFAULT_TEXT_SEARCH_CONFIG) -> None:
        self._config = text_search_config

    def upsert(self, documents: Iterable[SearchDocument]) -> None:
        for chunk in batched(documents, BATCH_SIZE):
            self._upsert_chunk(chunk)

    def delete(self, ids: Iterable[str]) -> None:
        for chunk in batched(ids, BATCH_SIZE):
            SearchIndexEntry.objects.filter(document_id__in=chunk).delete()

    def replace_all(self, documents: Iterable[SearchDocument]) -> None:
        """Delete and refill in one transaction.

        Readers keep seeing the old rows until commit and a failure while
        streaming rolls everything back. `DELETE` rather than `TRUNCATE`: the
        latter takes an exclusive lock that would block concurrent queries.
        """
        with transaction.atomic():
            SearchIndexEntry.objects.all().delete()
            self.upsert(documents)

    def query(
        self,
        text: str,
        *,
        kinds: Collection[str] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[SearchCandidate]:
        # `plain` parsing treats the text as data: every character that is
        # meaningful in tsquery syntax is ignored, terms are ANDed.
        search_query = SearchQuery(text, config=self._config, search_type="plain")
        entries = SearchIndexEntry.objects.filter(search_vector=search_query)
        if kinds is not None:
            entries = entries.filter(kind__in=kinds)
        rows = (
            entries.annotate(rank=SearchRank(F("search_vector"), search_query))
            .order_by("-rank", "document_id")
            .values_list("document_id", "rank")[offset : offset + limit]
        )
        return [SearchCandidate(id=doc_id, score=float(rank)) for doc_id, rank in rows]

    def health(self) -> EngineHealth:
        try:
            count = SearchIndexEntry.objects.count()
        except DatabaseError as exc:
            return EngineHealth(ok=False, detail=str(exc))
        return EngineHealth(ok=True, document_count=count)

    def _upsert_chunk(self, chunk: tuple[SearchDocument, ...]) -> None:
        # One statement cannot update the same row twice: the last duplicate wins.
        latest = {document.id: document for document in chunk}
        SearchIndexEntry.objects.bulk_create(
            list(self._entries(latest.values())),
            update_conflicts=True,
            unique_fields=["document_id"],
            update_fields=["kind", "title", "body", "search_vector"],
        )

    def _entries(
        self, documents: Iterable[SearchDocument]
    ) -> Iterator[SearchIndexEntry]:
        for document in documents:
            vector = SearchVector(
                Value(document.title), weight=TITLE_WEIGHT, config=self._config
            ) + SearchVector(
                Value(document.body), weight=BODY_WEIGHT, config=self._config
            )
            yield SearchIndexEntry(
                document_id=document.id,
                kind=document.kind,
                title=document.title,
                body=document.body,
                search_vector=vector,
            )
