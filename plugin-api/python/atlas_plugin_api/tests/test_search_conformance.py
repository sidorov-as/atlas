"""Run the engine conformance suite against a reference in-memory engine.

Proves the suite is satisfiable and gives adapter authors a worked example.
"""

import re

from atlas_plugin_api import (
    EngineCapabilities,
    EngineHealth,
    SearchCandidate,
)
from atlas_plugin_api.search_conformance import SearchEngineConformance


class InMemoryEngine:
    id = "in-memory"
    capabilities = EngineCapabilities()

    def __init__(self):
        self._docs = {}

    def upsert(self, documents):
        for doc in documents:
            self._docs[doc.id] = doc

    def delete(self, ids):
        for doc_id in ids:
            self._docs.pop(doc_id, None)

    def replace_all(self, documents):
        fresh = {doc.id: doc for doc in documents}  # consumed fully before swap
        self._docs = fresh

    def query(self, text, *, kinds=None, limit=20, offset=0):
        terms = re.findall(r"\w+", text.lower())
        if not terms:
            return []
        scored = []
        for doc in self._docs.values():
            if kinds is not None and doc.kind not in kinds:
                continue
            title, body = doc.title.lower(), doc.body.lower()
            score = sum(3 * title.count(t) + body.count(t) for t in terms)
            if score:
                scored.append(SearchCandidate(id=doc.id, score=float(score)))
        scored.sort(key=lambda c: (-c.score, c.id))
        return scored[offset : offset + limit]

    def health(self):
        return EngineHealth(ok=True, document_count=len(self._docs))


class TestInMemoryEngine(SearchEngineConformance):
    def make_engine(self):
        return InMemoryEngine()
