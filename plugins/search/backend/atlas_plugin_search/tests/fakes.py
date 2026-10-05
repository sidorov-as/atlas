"""An in-memory engine and a catalog-backed source for the plugin's tests."""

from collections.abc import Collection, Iterable, Iterator, Sequence

from atlas_plugin_api import (
    EngineCapabilities,
    EngineHealth,
    SearchCandidate,
    SearchDocument,
    SearchHit,
    get_catalog_entity_model,
)

KIND = "note"
SECRET_PREFIX = "secret"


class FakeEngine:
    """Word-prefix matching, title matches ranked above body matches."""

    def __init__(self, engine_id: str = "fake", *, highlights: bool = False):
        self.id = engine_id
        self.capabilities = EngineCapabilities(highlights=highlights)
        self.documents: dict[str, SearchDocument] = {}
        self.fail = False
        self.queries: list[str] = []

    def _check(self) -> None:
        if self.fail:
            raise ConnectionError("engine is down")

    def upsert(self, documents: Iterable[SearchDocument]) -> None:
        self._check()
        for document in documents:
            self.documents[document.id] = document

    def delete(self, ids: Iterable[str]) -> None:
        self._check()
        for document_id in ids:
            self.documents.pop(document_id, None)

    def replace_all(self, documents: Iterable[SearchDocument]) -> None:
        self._check()
        fresh = {document.id: document for document in documents}
        self.documents = fresh

    def query(
        self,
        text: str,
        *,
        kinds: Collection[str] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Sequence[SearchCandidate]:
        self._check()
        self.queries.append(text)
        terms = text.lower().split()
        scored = []
        for document in self.documents.values():
            if kinds and document.kind not in kinds:
                continue
            title = document.title.lower().split()
            body = document.body.lower().split()
            score = 0.0
            for term in terms:
                score += 2 * any(w.startswith(term) for w in title)
                score += any(w.startswith(term) for w in body)
            if score:
                highlight = document.summary if self.capabilities.highlights else None
                scored.append(SearchCandidate(document.id, score, highlight))
        scored.sort(key=lambda c: (-c.score, c.id))
        return scored[offset : offset + limit]

    def health(self) -> EngineHealth:
        if self.fail:
            return EngineHealth(ok=False, detail="engine is down")
        return EngineHealth(ok=True, document_count=len(self.documents))


def _document(entity) -> SearchDocument:
    return SearchDocument(
        id=f"{KIND}:{entity.pk}",
        kind=KIND,
        title=entity.name,
        body=entity.description or "",
        summary=entity.description or None,
    )


class CatalogNoteSource:
    """Catalog entities as `note` documents; names starting with `secret`
    are readable by superusers only."""

    id = "notes"
    kinds = (KIND,)

    @property
    def watched_models(self):
        return (get_catalog_entity_model()._meta.label,)

    def __init__(self) -> None:
        self.failing_documents = False

    def document_ids_for_instance(self, instance) -> Iterable[str]:
        return [f"{KIND}:{instance.pk}"]

    def documents(self, ids: Sequence[str]) -> Iterable[SearchDocument]:
        if self.failing_documents:
            raise RuntimeError("source is broken")
        pks = [i.partition(":")[2] for i in ids]
        return [
            _document(e) for e in get_catalog_entity_model().objects.filter(pk__in=pks)
        ]

    def all_documents(self) -> Iterator[SearchDocument]:
        for entity in get_catalog_entity_model().objects.all():
            yield _document(entity)

    def resolve(self, ids: Sequence[str], actor) -> Sequence[SearchHit]:
        pks = [i.partition(":")[2] for i in ids]
        hits = []
        for entity in get_catalog_entity_model().objects.filter(pk__in=pks):
            if entity.name.startswith(SECRET_PREFIX) and not actor.is_superuser:
                continue
            hits.append(
                SearchHit(
                    id=f"{KIND}:{entity.pk}",
                    kind=KIND,
                    title=entity.name,
                    link=f"/catalog/{entity.pk}",
                    text=entity.description or "",
                    summary=entity.description or None,
                )
            )
        return hits
