"""Conformance suite for search engine adapters.

An adapter author subclasses ``SearchEngineConformance`` in their own tests
and implements ``make_engine``; pytest then runs every portable check
against the adapter::

    class TestMyEngine(SearchEngineConformance):
        def make_engine(self):
            return MyEngine(...)

``make_engine`` must return an engine whose index is empty and isolated from
other tests. The class name deliberately lacks a ``Test`` prefix so importing
it does not make pytest collect the suite itself.
"""

from __future__ import annotations

import pytest

from .search import (
    EngineCapabilities,
    EngineHealth,
    SearchDocument,
    SearchEngine,
)


def _doc(key: str, title: str, body: str = "", kind: str = "note") -> SearchDocument:
    return SearchDocument(id=f"{kind}:{key}", kind=kind, title=title, body=body)


def _ids(candidates) -> list[str]:
    return [c.id for c in candidates]


class SearchEngineConformance:
    def make_engine(self) -> SearchEngine:
        raise NotImplementedError("subclasses must implement make_engine()")

    @pytest.fixture
    def engine(self) -> SearchEngine:
        return self.make_engine()

    def test_declares_id_and_capabilities(self, engine):
        assert isinstance(engine, SearchEngine)
        assert engine.id
        assert isinstance(engine.capabilities, EngineCapabilities)

    def test_health_reports_ok_for_a_working_engine(self, engine):
        health = engine.health()
        assert isinstance(health, EngineHealth)
        assert health.ok

    def test_upsert_makes_documents_queryable(self, engine):
        engine.upsert([_doc("1", "Payment gateway", "handles card payments")])
        assert _ids(engine.query("payment")) == ["note:1"]

    def test_upsert_replaces_an_existing_document(self, engine):
        engine.upsert([_doc("1", "Alpha service")])
        engine.upsert([_doc("1", "Beta service")])
        assert _ids(engine.query("alpha")) == []
        assert _ids(engine.query("beta")) == ["note:1"]

    def test_delete_removes_documents_and_ignores_unknown_ids(self, engine):
        engine.upsert([_doc("1", "Gateway"), _doc("2", "Gateway proxy")])
        engine.delete(["note:1", "note:missing"])
        assert _ids(engine.query("gateway")) == ["note:2"]

    def test_query_without_matches_returns_nothing(self, engine):
        engine.upsert([_doc("1", "Gateway")])
        assert list(engine.query("zzzzzz")) == []

    def test_query_on_empty_index_returns_nothing(self, engine):
        assert list(engine.query("anything")) == []

    def test_candidates_carry_scores_in_descending_order(self, engine):
        engine.upsert(
            [
                _doc("1", "Billing", "mentions gateway once"),
                _doc("2", "Gateway", "gateway gateway gateway"),
            ]
        )
        candidates = list(engine.query("gateway"))
        assert len(candidates) == 2
        scores = [c.score for c in candidates]
        assert scores == sorted(scores, reverse=True)

    def test_title_match_outranks_body_match(self, engine):
        engine.upsert(
            [
                _doc("body", "Billing", "the gateway sits in front"),
                _doc("title", "Gateway", "routes requests"),
            ]
        )
        assert _ids(engine.query("gateway"))[0] == "note:title"

    def test_kind_filter(self, engine):
        engine.upsert(
            [
                _doc("1", "Gateway", kind="note"),
                _doc("2", "Gateway", kind="task"),
            ]
        )
        assert _ids(engine.query("gateway", kinds=["task"])) == ["task:2"]
        assert sorted(_ids(engine.query("gateway", kinds=["note", "task"]))) == [
            "note:1",
            "task:2",
        ]

    def test_limit_and_offset_paginate_without_overlap(self, engine):
        engine.upsert([_doc(str(i), f"Gateway {i}") for i in range(5)])
        everything = _ids(engine.query("gateway", limit=10))
        assert len(everything) == 5
        first = _ids(engine.query("gateway", limit=2, offset=0))
        second = _ids(engine.query("gateway", limit=2, offset=2))
        third = _ids(engine.query("gateway", limit=2, offset=4))
        assert first + second + third == everything

    def test_query_with_special_characters_does_not_raise(self, engine):
        engine.upsert([_doc("1", "Gateway")])
        for text in ("'", '"', "&", "|", "!", ":*", "(", "a & | b", "\\", "gateway'"):
            list(engine.query(text))

    def test_replace_all_replaces_the_whole_index(self, engine):
        engine.upsert([_doc("1", "Old gateway")])
        engine.replace_all([_doc("2", "New gateway")])
        assert _ids(engine.query("gateway")) == ["note:2"]

    def test_replace_all_with_no_documents_empties_the_index(self, engine):
        engine.upsert([_doc("1", "Gateway")])
        engine.replace_all([])
        assert list(engine.query("gateway")) == []

    def test_failed_replace_all_keeps_previous_content(self, engine):
        engine.upsert([_doc("1", "Old gateway")])

        def broken():
            yield _doc("2", "New gateway")
            raise RuntimeError("source failed midway")

        with pytest.raises(RuntimeError):
            engine.replace_all(broken())
        assert _ids(engine.query("gateway")) == ["note:1"]

    def test_highlights_only_when_declared(self, engine):
        engine.upsert([_doc("1", "Gateway", "routes requests")])
        for candidate in engine.query("gateway"):
            if not engine.capabilities.highlights:
                assert candidate.highlight is None
