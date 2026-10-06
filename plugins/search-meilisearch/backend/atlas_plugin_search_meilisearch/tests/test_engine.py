"""Request-level tests against a stubbed client; the real instance is covered
by `test_conformance.py`."""

import pytest
from atlas_plugin_api import SearchDocument

from atlas_plugin_search_meilisearch.client import (
    MeilisearchApiError,
    MeilisearchError,
)
from atlas_plugin_search_meilisearch.config import SearchMeilisearchPluginConfig
from atlas_plugin_search_meilisearch.engine import (
    INDEX_SETTINGS,
    MeilisearchSearchEngine,
    to_highlight,
    to_plain_highlight,
)


class StubClient:
    def __init__(self):
        self.calls = []
        self.exists = True
        self.fail_on = None
        self.search_result = {"hits": []}

    def request(self, method, path, *, json=None, timeout=None):
        self.calls.append((method, path, json))
        if method == "GET" and path.endswith("/stats"):
            return {"numberOfDocuments": 7}
        if method == "GET" and path.startswith("/indexes/") and not self.exists:
            raise MeilisearchApiError(404, "index_not_found", "missing")
        if path.endswith("/search"):
            return self.search_result
        return {}

    def run_task(self, method, path, *, json=None):
        self.calls.append((method, path, json))
        if self.fail_on and self.fail_on in path:
            raise MeilisearchError("task failed")
        return {}

    def paths(self, method=None):
        return [p for m, p, _ in self.calls if method in (None, m)]


@pytest.fixture
def engine():
    engine = MeilisearchSearchEngine(
        SearchMeilisearchPluginConfig(url="http://meili:7700", index="idx")
    )
    engine._client = StubClient()
    return engine


def _doc(key="1", title="Gateway", **kw):
    return SearchDocument(id=f"note:{key}", kind="note", title=title, **kw)


def test_declares_native_capabilities(engine):
    assert engine.capabilities.highlights
    assert engine.capabilities.typo_tolerance


def test_upsert_stores_an_encoded_id_and_the_original(engine):
    engine.upsert([_doc("a b", body="text", summary="s", route="r")])

    (_, path, payload) = next(c for c in engine._client.calls if "documents" in c[1])
    assert path == "/indexes/idx/documents?primaryKey=id"
    (document,) = payload
    assert document["document_id"] == "note:a b"
    assert document["id"] == "note_3aa_20b"
    assert document["kind"] == "note"


def test_upsert_collapses_duplicates_in_a_batch(engine):
    engine.upsert([_doc("1", "Old"), _doc("1", "New")])
    (_, _, payload) = next(c for c in engine._client.calls if "documents" in c[1])
    assert [d["title"] for d in payload] == ["New"]


def test_a_missing_index_is_created_with_ranked_settings(engine):
    engine._client.exists = False
    engine.upsert([_doc()])

    assert ("POST", "/indexes") in [(m, p) for m, p, _ in engine._client.calls]
    settings = next(j for m, p, j in engine._client.calls if p.endswith("/settings"))
    assert settings == INDEX_SETTINGS
    assert settings["searchableAttributes"] == ["title", "summary", "body"]
    assert "kind" in settings["filterableAttributes"]


def test_a_write_failure_is_surfaced(engine):
    engine._client.fail_on = "/documents"
    with pytest.raises(MeilisearchError):
        engine.upsert([_doc()])


def test_delete_sends_encoded_ids(engine):
    engine.delete(["note:a/b"])
    (_, path, payload) = engine._client.calls[-1]
    assert path == "/indexes/idx/documents/delete-batch"
    assert payload == ["note_3aa_2fb"]


def test_replace_all_builds_a_temporary_index_then_swaps_and_drops_it(engine):
    engine.replace_all([_doc("1"), _doc("2")])

    calls = engine._client.calls
    temp = next(j["uid"] for m, p, j in calls if (m, p) == ("POST", "/indexes"))
    assert temp.startswith("idx-build-")
    swap = next(j for m, p, j in calls if p == "/swap-indexes")
    assert swap == [{"indexes": ["idx", temp]}]
    assert calls[-1][:2] == ("DELETE", f"/indexes/{temp}")
    assert [p for _, p, _ in calls].index("/swap-indexes") < len(calls) - 1
    assert all("idx/documents" not in p for _, p, _ in calls)


def test_a_failed_replace_all_discards_the_temporary_index_and_never_swaps(engine):
    def broken():
        yield _doc("1")
        raise RuntimeError("source failed")

    with pytest.raises(RuntimeError):
        engine.replace_all(broken())

    paths = engine._client.paths()
    assert "/swap-indexes" not in paths
    assert engine._client.calls[-1][0] == "DELETE"
    assert "-build-" in engine._client.calls[-1][1]


def test_a_failed_swap_discards_the_temporary_index(engine):
    engine._client.fail_on = "/swap-indexes"
    with pytest.raises(MeilisearchError):
        engine.replace_all([_doc()])
    assert engine._client.calls[-1][:1] == ("DELETE",)


def test_query_filters_by_kind_and_maps_hits(engine):
    engine._client.search_result = {
        "hits": [
            {
                "document_id": "note:a b",
                "_rankingScore": 0.9,
                "_formatted": {"body": "…the gateway routes", "summary": ""},
            },
            {"document_id": "note:2", "_rankingScore": 0.5, "_formatted": {}},
        ]
    }
    candidates = engine.query("gateway", kinds=["note", 'we"ird'], limit=5, offset=10)

    (_, path, payload) = engine._client.calls[-1]
    assert path == "/indexes/idx/search"
    assert payload["filter"] == 'kind IN ["note", "we\\"ird"]'
    assert (payload["limit"], payload["offset"]) == (5, 10)
    assert [c.id for c in candidates] == ["note:a b", "note:2"]
    assert candidates[0].score == 0.9
    assert candidates[0].highlight == "…the gateway routes"
    assert candidates[1].highlight is None


def test_blank_query_and_empty_kinds_return_nothing_without_a_request(engine):
    assert engine.query("   ") == []
    assert engine.query("gateway", kinds=[]) == []
    assert engine._client.calls == []


def test_query_on_a_missing_index_is_empty(engine):
    def missing(*a, **k):
        raise MeilisearchApiError(404, "index_not_found", "x")

    engine._client.request = missing
    assert engine.query("gateway") == []


def test_highlight_never_carries_markup():
    text = to_plain_highlight(
        "<script>alert(1)</script> a <b>pay</b>ment <!-- x --> done"
    )
    assert "<" not in text and ">" not in text
    assert "" not in text and "" not in text
    assert "payment" in text.replace(" ", "")


S, E = "\ue000", "\ue001"


def _marked(text, matches):
    return [text[a:b] for a, b in matches]


def test_highlight_offsets_address_the_plain_text():
    text, matches = to_highlight(f"…the {S}payment{E} gateway")

    assert text == "…the payment gateway"
    assert _marked(text, matches) == ["payment"]


def test_highlight_offsets_cover_every_marked_word():
    text, matches = to_highlight(f"{S}pay{E} the {S}gateway{E}")

    assert _marked(text, matches) == ["pay", "gateway"]


def test_offsets_follow_text_changed_by_cleaning():
    text, matches = to_highlight(
        f"  <p>a</p>\n\n  <b>old</b>   {S}paymnt{E}\t<!-- x -->  {S}gate{E}way "
    )

    assert text == "a old paymnt gateway"
    assert _marked(text, matches) == ["paymnt", "gateway"]


def test_offsets_are_in_code_points_beyond_the_bmp():
    text, matches = to_highlight(f"\U0001f600 {S}pay\U0001f600ment{E}")

    assert _marked(text, matches) == ["pay\U0001f600ment"]
    assert matches == ((2, 10),)


def test_a_marker_lost_inside_a_tag_leaves_no_wrong_mark():
    text, matches = to_highlight(f'x <a href="{S}u{E}">{S}y{E}</a> {S}z')

    assert text == "x y z"
    assert _marked(text, matches) == ["y"]


def test_stray_and_nested_markers_are_dropped():
    text, matches = to_highlight(f"a {E}b {S}c {S}d{E} e{E} f")

    assert text == "a b c d e f"
    assert _marked(text, matches) == ["c d"]


def test_whitespace_around_a_match_is_not_marked():
    text, matches = to_highlight(f"a{S} word {E}b")

    assert _marked(text, matches) == ["word"]
    assert to_highlight(f"a{S}  {E}b")[1] == ()


def _words(formatted):
    text, matches = to_highlight(formatted)
    return _marked(text, matches)


def test_a_partly_marked_word_is_marked_whole():
    # The engine marks only the matched part of a word for a typo or a prefix.
    assert _words(f"The {S}paymen{E}t gateway") == ["payment"]
    assert _words(f"card {S}payment{E}s ok") == ["payments"]
    assert _words(f"a {S}pa{E}yment {S}gat{E}eway") == ["payment", "gateway"]


def test_a_partly_marked_cyrillic_word_is_marked_whole():
    assert _words(f"обрабатывает {S}платеж{E}и клиентов") == ["платежи"]


def test_words_end_where_the_engine_ends_them():
    # `_`, `-` and camelCase are word boundaries for the engine.
    assert _words(f"call {S}payment{E}_gateway and {S}billing{E}-api") == [
        "payment",
        "billing",
    ]
    assert _words(f"the {S}Paymen{E}tGateway class") == ["Payment"]
    assert _words(f"the {S}Payment{E}Gateway class") == ["Payment"]


def test_scripts_written_without_spaces_are_not_widened():
    assert _words(f"这是{S}支付{E}网关服务") == ["支付"]
    assert _words(f"決済ゲートウェイは{S}支払{E}いを処理します") == ["支払"]
    assert _words(f"การ{S}ชำระ{E}เงิน") == ["ชำระ"]


def test_widening_stops_at_whitespace_punctuation_and_text_ends():
    assert _words(f"({S}paymen{E}t), {S}gatewa{E}y.") == ["payment", "gateway"]
    assert _words(f"{S}paymen{E}t") == ["payment"]


def test_ranges_of_one_word_are_joined():
    text, matches = to_highlight(f"{S}pay{E}{S}ment{E} {S}pay{E}ment x")

    assert _marked(text, matches) == ["payment", "payment"]
    assert matches == ((0, 7), (8, 15))


def test_widening_counts_code_points_beyond_the_bmp():
    text, matches = to_highlight(f"\U0001f600 {S}pay{E}ment \U0001f600 {S}pa{E}y")

    assert _marked(text, matches) == ["payment", "pay"]
    assert matches == ((2, 9), (12, 15))


def test_text_without_markers_has_no_offsets():
    assert to_highlight("<b>plain</b>  text") == ("plain text", ())


def test_candidate_carries_the_offsets_of_a_typo_match(engine):
    engine._client.search_result = {
        "hits": [
            {
                "document_id": "note:1",
                "_rankingScore": 0.8,
                "_formatted": {"body": f"a <i>{S}payment{E}</i>  gateway"},
            },
            {
                "document_id": "note:2",
                "_rankingScore": 0.5,
                "_formatted": {"summary": f"{S}pay{E} me"},
            },
        ]
    }

    first, second = engine.query("paymnt")

    assert first.highlight == "a payment gateway"
    assert _marked(first.highlight, first.highlight_matches) == ["payment"]
    assert _marked(second.highlight, second.highlight_matches) == ["pay"]


def test_health_reports_the_document_count(engine):
    health = engine.health()
    assert health.ok and health.document_count == 7


def test_health_reports_a_missing_index_as_empty_and_down_instance_as_unhealthy(engine):
    engine._client.exists = False
    stats = engine._client.request

    def missing_stats(method, path, **kw):
        if path.endswith("/stats"):
            raise MeilisearchApiError(404, "index_not_found", "x")
        return stats(method, path, **kw)

    engine._client.request = missing_stats
    assert engine.health().document_count == 0

    def down(*a, **k):
        raise MeilisearchError("Meilisearch is unreachable at http://meili:7700")

    engine._client.request = down
    health = engine.health()
    assert not health.ok
    assert "unreachable" in health.detail


def test_an_unresolved_secret_reference_is_rejected():
    config = SearchMeilisearchPluginConfig(url="http://m", key={"fromEnv": "K"})
    with pytest.raises(ValueError, match="'key'"):
        MeilisearchSearchEngine(config)
