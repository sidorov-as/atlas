from typing import ClassVar

import pytest
from atlas_plugin_api import SearchCandidate, SearchDocument, SearchHit
from atlas_plugin_api import search as search_contract

from atlas_plugin_search import indexer, runtime
from atlas_plugin_search.config import SearchPluginConfig
from atlas_plugin_search.models import PendingChange

SEARCH = "/api/plugins/atlas.search/search/"
STATUS = "/api/plugins/atlas.search/status/"


@pytest.fixture
def indexed(active, make_note):
    def _index(*names_and_descriptions):
        notes = [make_note(*item) for item in names_and_descriptions]
        indexer.drain_pending()
        return notes

    return _index


def _search(client, **params):
    return client.get(SEARCH, data=params)


def test_unauthenticated_request_is_denied(dmr_client, active):
    response = _search(dmr_client, q="payment")

    assert response.status_code in (401, 403)


def test_basic_query_returns_ranked_results_with_the_contract_fields(
    user_client, indexed
):
    body_match, title_match = indexed(
        ("billing", "handles payment retries"),
        ("payment gateway", "settles card payments"),
    )

    response = _search(user_client, q="payment")

    assert response.status_code == 200
    data = response.json()
    assert [r["id"] for r in data["results"]] == [
        f"note:{title_match.pk}",
        f"note:{body_match.pk}",
    ]
    first = data["results"][0]
    assert first["kind"] == "note"
    assert first["kindLabel"] == "Note"
    assert first["title"] == "payment gateway"
    assert first["link"] == f"/catalog/{title_match.pk}"
    assert first["snippet"]["text"] == "settles card payments"
    assert first["snippet"]["matches"] == [[13, 21]]
    assert data["total"] == 2
    assert data["hasMore"] is False
    assert data["page"] == 1


def test_kind_filter_limits_results(user_client, indexed):
    (note,) = indexed(("payment gateway", ""))

    assert _search(user_client, q="payment", kinds="note").json()["total"] == 1
    assert _search(user_client, q="payment", kinds="flow").json()["results"] == []
    assert _search(user_client, q="payment", kinds="flow,note").json()["total"] == 1
    assert note


class _StaticFlowSource:
    """A second kind (`flow`) with fixed documents, for facet tests."""

    id = "flows"
    kinds = ("flow",)
    kind_labels: ClassVar[dict[str, str]] = {"flow": "Flow"}
    watched_models = ()
    TITLES: ClassVar[dict[str, str]] = {"1": "payment flow", "2": "refund payment flow"}

    def document_ids_for_instance(self, instance):
        return []

    def documents(self, ids):
        return [d for d in self.all_documents() if d.id in set(ids)]

    def all_documents(self):
        for pk, title in self.TITLES.items():
            yield SearchDocument(
                id=f"flow:{pk}", kind="flow", title=title, body="", summary=None
            )

    def resolve(self, ids, actor):
        return [
            SearchHit(
                id=f"flow:{pk}",
                kind="flow",
                title=self.TITLES[pk],
                link=f"/flows/{pk}",
                text="",
                summary=None,
            )
            for pk in (i.partition(":")[2] for i in ids)
            if pk in self.TITLES
        ]


@pytest.fixture
def two_kinds(activate, make_note):
    search_contract.register_search_source(_StaticFlowSource(), owner="test.flows")
    activate()
    make_note("payment gateway", "")
    make_note("billing", "handles payment retries")
    indexer.rebuild_index()


def test_facets_are_absent_unless_requested(user_client, two_kinds):
    assert _search(user_client, q="payment").json()["facets"] is None


def test_facets_count_authorized_hits_per_kind(user_client, two_kinds):
    data = _search(user_client, q="payment", facets="true").json()

    assert data["facets"] == [
        {"kind": "flow", "kindLabel": "Flow", "count": 2},
        {"kind": "note", "kindLabel": "Note", "count": 2},
    ]
    assert data["total"] == 4


def test_facets_ignore_the_kind_filter_but_results_obey_it(user_client, two_kinds):
    data = _search(user_client, q="payment", kinds="flow", facets="true").json()

    assert {r["kind"] for r in data["results"]} == {"flow"}
    assert data["total"] == 2
    assert {f["kind"]: f["count"] for f in data["facets"]} == {"flow": 2, "note": 2}


def test_facets_do_not_count_unreadable_documents(
    dmr_client, user, superuser, active, make_note
):
    make_note("secret payment plan", "")
    make_note("payment gateway", "")
    indexer.rebuild_index()

    dmr_client.force_login(user)
    regular = _search(dmr_client, q="payment", facets="true").json()
    dmr_client.force_login(superuser)
    admin = _search(dmr_client, q="payment", facets="true").json()

    assert [f["count"] for f in regular["facets"]] == [1]
    assert [f["count"] for f in admin["facets"]] == [2]


def test_facet_results_are_paginated_after_filtering(user_client, two_kinds):
    data = _search(
        user_client, q="payment", kinds="note", facets="true", page_size=1
    ).json()

    assert len(data["results"]) == 1
    assert data["total"] == 2
    assert data["hasMore"] is True


def test_short_or_empty_query_returns_nothing_without_querying_the_engine(
    user_client, indexed, engine
):
    indexed(("payment gateway", ""))

    for query in ("", "p", "   "):
        response = _search(user_client, q=query)
        assert response.status_code == 200
        assert response.json()["results"] == []
    assert engine.queries == []


def test_minimum_query_length_is_configurable(user_client, activate, make_note, engine):
    activate(SearchPluginConfig(minQueryLength=4))
    make_note("payment gateway")
    indexer.drain_pending()

    assert _search(user_client, q="pay").json()["results"] == []
    assert len(_search(user_client, q="paym").json()["results"]) == 1


def test_unreadable_documents_are_absent_from_results_and_total(
    dmr_client, user, superuser, indexed
):
    indexed(("secret payment plan", ""), ("payment gateway", ""))

    dmr_client.force_login(user)
    visible = _search(dmr_client, q="payment").json()
    assert [r["title"] for r in visible["results"]] == ["payment gateway"]
    assert visible["total"] == 1

    dmr_client.force_login(superuser)
    admin_view = _search(dmr_client, q="payment").json()
    assert admin_view["total"] == 2


def test_document_deleted_while_still_indexed_is_omitted(user_client, indexed):
    (note,) = indexed(("payment gateway", ""))
    type(note).objects.filter(pk=note.pk).delete()  # signal-less: index is stale
    PendingChange.objects.all().delete()

    assert _search(user_client, q="payment").json()["results"] == []


def test_pages_are_filled_past_filtered_candidates(user_client, indexed):
    # Secret documents rank first, so every early candidate is filtered out.
    indexed(
        *[(f"secret payment {i}", "") for i in range(8)],
        *[(f"payment {i}", "") for i in range(5)],
    )

    data = _search(user_client, q="payment", page_size=3).json()

    assert len(data["results"]) == 3
    assert data["hasMore"] is True
    assert data["total"] == 5  # every candidate was examined: exact

    second = _search(user_client, q="payment", page_size=3, page=2).json()
    assert len(second["results"]) == 2
    assert second["hasMore"] is False
    assert second["total"] == 5
    assert not {r["id"] for r in data["results"]} & {r["id"] for r in second["results"]}


def test_page_size_is_capped(user_client, indexed):
    indexed(("payment gateway", ""))

    assert _search(user_client, q="payment", page_size=500).status_code == 400
    assert _search(user_client, q="payment", page=0).status_code == 400


def test_engine_failure_is_a_service_unavailable_response(user_client, indexed, engine):
    indexed(("payment gateway", ""))
    engine.fail = True

    response = _search(user_client, q="payment")

    assert response.status_code == 503


def test_snippet_of_a_title_only_match_falls_back_to_the_summary(user_client, indexed):
    indexed(("payment gateway", "unrelated words only"))

    snippet = _search(user_client, q="payment").json()["results"][0]["snippet"]

    assert snippet == {"text": "unrelated words only", "matches": []}


def test_markup_in_indexed_text_does_not_reach_the_snippet(user_client, indexed):
    indexed(("note", "see <script>alert(1)</script> the payment gateway"))

    snippet = _search(user_client, q="payment").json()["results"][0]["snippet"]

    assert "<" not in snippet["text"]
    assert snippet["text"][snippet["matches"][0][0] : snippet["matches"][0][1]] == (
        "payment"
    )


def test_engine_supplied_highlights_override_core_snippets(
    user_client, activate, make_note, engine
):
    engine.capabilities = type(engine.capabilities)(highlights=True)
    activate()
    make_note("note", "core would use this body text for payment")
    indexer.drain_pending()
    # The fake engine returns the document summary as its highlight.
    engine.documents = {
        k: SearchDocument(
            id=d.id,
            kind=d.kind,
            title=d.title,
            body=d.body,
            summary="engine <b>highlight</b> for payment",
        )
        for k, d in engine.documents.items()
    }

    snippet = _search(user_client, q="payment").json()["results"][0]["snippet"]

    assert snippet["text"] == "engine highlight for payment"


def test_engine_offsets_mark_matches_the_query_does_not_prefix(
    user_client, activate, make_note, engine
):
    engine.capabilities = type(engine.capabilities)(highlights=True)
    activate()
    make_note("note", "the payment gateway")
    indexer.drain_pending()
    highlight = "the payment gateway"
    real_query = engine.query

    def query(text, **kwargs):
        return [
            SearchCandidate(c.id, c.score, highlight, ((4, 11),))
            for c in real_query("payment", **kwargs)
        ]

    engine.query = query

    snippet = _search(user_client, q="paymnt").json()["results"][0]["snippet"]

    assert snippet["text"] == highlight
    assert snippet["matches"] == [[4, 11]]


def test_snippet_offsets_are_utf16_code_units(user_client, indexed):
    indexed(("billing", "\U0001f600 payment gateway"))

    snippet = _search(user_client, q="payment").json()["results"][0]["snippet"]

    units = snippet["text"].encode("utf-16-le")
    marked = [units[2 * a : 2 * b].decode("utf-16-le") for a, b in snippet["matches"]]
    assert marked == ["payment"]


def test_a_broken_source_does_not_fail_the_request(user_client, indexed, source):
    indexed(("payment gateway", ""))

    def broken(ids, actor):
        raise RuntimeError("resolve exploded")

    source.resolve = broken

    response = _search(user_client, q="payment")

    assert response.status_code == 200
    assert response.json()["results"] == []


def test_search_endpoint_is_inert_when_the_plugin_is_not_active(user_client):
    assert not runtime.is_active()

    assert _search(user_client, q="payment").status_code == 404
    assert user_client.get(STATUS).status_code == 404


def test_status_for_a_regular_user_is_limited(user_client, indexed, engine, make_note):
    indexed(("payment gateway", ""))
    make_note("pending one")
    engine.fail = False

    data = user_client.get(STATUS).json()

    assert data["ok"] is True
    assert data["engineHealthy"] is True
    assert data["pendingCount"] == 1
    assert isinstance(data["oldestPendingAgeSeconds"], int)
    assert data["lastDrainAt"] is not None
    assert data["lastRebuildAt"] is None
    assert data["hasError"] is False
    for admin_only in (
        "engine",
        "engineDetail",
        "documentCount",
        "lastError",
        "lastErrorAt",
        "lastErrorJob",
        "drainIntervalSeconds",
        "rebuildIntervalSeconds",
    ):
        assert data.get(admin_only) is None


def test_status_for_an_administrator_has_full_detail(
    superuser_client, indexed, engine, make_note
):
    indexed(("payment gateway", ""))
    make_note("pending one")
    engine.fail = True
    indexer.drain_pending()

    data = superuser_client.get(STATUS).json()

    assert data["ok"] is False
    assert data["engine"] == "fake"
    assert data["engineHealthy"] is False
    assert data["engineDetail"] == "engine is down"
    assert data["hasError"] is True
    assert "engine is down" in data["lastError"]
    assert data["lastErrorJob"] == "drain"
    assert data["lastErrorAt"] is not None
    assert data["drainIntervalSeconds"] == 10
    assert data["rebuildIntervalSeconds"] == 21600


def test_status_hides_error_text_from_regular_users(
    user_client, indexed, engine, make_note
):
    indexed(("payment gateway", ""))
    make_note("pending one")
    engine.fail = True
    indexer.drain_pending()

    data = user_client.get(STATUS).json()

    assert data["ok"] is False
    assert data["hasError"] is True
    assert data["engineHealthy"] is False
    assert data.get("lastError") is None
    assert data.get("engineDetail") is None
    assert "engine is down" not in str(data)


def test_status_reports_no_backlog_when_nothing_is_pending(user_client, indexed):
    indexed(("payment gateway", ""))

    data = user_client.get(STATUS).json()

    assert data["pendingCount"] == 0
    assert data["oldestPendingAgeSeconds"] is None
