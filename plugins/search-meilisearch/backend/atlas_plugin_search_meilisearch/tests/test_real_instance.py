"""Adapter behaviour that the portable conformance suite does not cover,
against a real instance (`conftest.py`)."""

import pytest
from atlas_plugin_api import SearchDocument

from atlas_plugin_search_meilisearch.client import MeilisearchClient
from atlas_plugin_search_meilisearch.ids import MAX_ENCODED_LENGTH

AWKWARD_IDS = [
    "note:1",
    "api:payments/v1 beta",
    "kind:ключ-ü",
    "a_b:c_d",
    "a:b:c",
    "k:_",
    "k:_5f",
    "k:%/?#&=+",
    "note:" + "ü" * 500,
]


def _doc(document_id, title="Gateway", kind=None, **kw):
    kind = kind or document_id.partition(":")[0]
    return SearchDocument(id=document_id, kind=kind, title=title, **kw)


def _ids(candidates):
    return [c.id for c in candidates]


def test_awkward_ids_are_indexed_separately_and_returned_unchanged(real_engine):
    real_engine.upsert([_doc(i, f"Gateway {n}") for n, i in enumerate(AWKWARD_IDS)])

    found = _ids(real_engine.query("gateway", limit=50))

    assert sorted(found) == sorted(AWKWARD_IDS)


def test_awkward_ids_can_be_deleted(real_engine):
    real_engine.upsert([_doc(i) for i in AWKWARD_IDS])

    real_engine.delete(AWKWARD_IDS[:-1])

    assert _ids(real_engine.query("gateway", limit=50)) == [AWKWARD_IDS[-1]]


def test_ids_that_differ_only_by_an_escape_lookalike_stay_distinct(real_engine):
    real_engine.upsert([_doc("k:_", "Gateway one"), _doc("k:_5f", "Gateway two")])

    assert sorted(_ids(real_engine.query("gateway"))) == ["k:_", "k:_5f"]


def test_an_id_longer_than_the_engine_limit_is_accepted(real_engine):
    long_id = "note:" + "x" * (MAX_ENCODED_LENGTH + 100)
    real_engine.upsert([_doc(long_id)])

    assert _ids(real_engine.query("gateway")) == [long_id]


def _assert_plain(highlight):
    for forbidden in ("<", ">", "\ue000", "\ue001"):
        assert forbidden not in highlight


def test_markup_in_content_never_reaches_the_highlight(real_engine):
    real_engine.upsert(
        [
            _doc(
                "note:1",
                "Gateway",
                body="intro <script>alert(1)</script> the gateway "
                "<img src=x onerror=alert(2)> routes <!-- c --> traffic",
                summary='<a href="javascript:x">top</a> gateway summary',
            )
        ]
    )

    (candidate,) = real_engine.query("gateway")

    assert candidate.highlight
    _assert_plain(candidate.highlight)
    assert "gateway" in candidate.highlight.lower()


def test_a_match_wrapped_in_markup_never_leaks_the_markup(real_engine):
    # Meilisearch does not mark a word glued to a tag, so there may be no
    # highlight at all; whatever is returned must still be plain text.
    real_engine.upsert(
        [_doc("note:1", "Gateway", body="intro <b>gateway</b> <script>x</script>")]
    )

    (candidate,) = real_engine.query("gateway")

    if candidate.highlight is not None:
        _assert_plain(candidate.highlight)


def test_a_match_only_in_the_title_has_no_highlight(real_engine):
    real_engine.upsert([_doc("note:1", "Gateway", body="routes requests")])

    (candidate,) = real_engine.query("gateway")

    assert candidate.highlight is None


@pytest.mark.parametrize(
    ("indexed", "typo"),
    [
        ("payment", "paymnet"),
        ("gateway", "gatewya"),
        ("authentication", "autentication"),
    ],
)
def test_a_small_typo_still_finds_the_document(real_engine, indexed, typo):
    real_engine.upsert([_doc("note:1", f"The {indexed} service")])

    assert _ids(real_engine.query(typo)) == ["note:1"]


def test_an_unrelated_word_is_not_matched_by_typo_tolerance(real_engine):
    real_engine.upsert([_doc("note:1", "Payment service")])

    assert real_engine.query("zebra") == []


def test_summary_ranks_between_title_and_body(real_engine):
    real_engine.upsert(
        [
            _doc("note:body", "Billing", body="the gateway sits in front"),
            _doc("note:summary", "Billing", summary="the gateway sits in front"),
            _doc("note:title", "Gateway"),
        ]
    )

    assert _ids(real_engine.query("gateway")) == [
        "note:title",
        "note:summary",
        "note:body",
    ]


def test_filter_by_kind(real_engine):
    real_engine.upsert(
        [
            _doc("note:1", kind="note"),
            _doc("task:1", kind="task"),
            _doc("doc:1", kind="doc"),
        ]
    )

    assert _ids(real_engine.query("gateway", kinds=["task"])) == ["task:1"]
    assert sorted(_ids(real_engine.query("gateway", kinds=["note", "doc"]))) == [
        "doc:1",
        "note:1",
    ]
    assert real_engine.query("gateway", kinds=[]) == []
    assert real_engine.query("gateway", kinds=["missing"]) == []


def test_kind_values_with_quotes_cannot_break_out_of_the_filter(real_engine):
    real_engine.upsert([_doc("note:1", kind="note")])

    assert real_engine.query("gateway", kinds=['x"] OR kind = "note']) == []


def test_blank_query_returns_nothing_instead_of_the_whole_index(real_engine):
    real_engine.upsert([_doc("note:1")])

    assert real_engine.query("   ") == []


def test_replace_all_leaves_no_temporary_index_behind(real_engine, meilisearch_config):
    real_engine.upsert([_doc("note:1")])
    real_engine.replace_all([_doc("note:2")])

    client = MeilisearchClient(
        meilisearch_config.url,
        meilisearch_config.key,
        request_timeout=10,
        task_timeout=30,
    )
    uids = [i["uid"] for i in client.request("GET", "/indexes?limit=1000")["results"]]
    leftovers = [
        uid for uid in uids if uid.startswith(f"{meilisearch_config.index}-build-")
    ]
    assert leftovers == []


def test_replace_all_keeps_the_index_settings(real_engine, meilisearch_config):
    real_engine.replace_all(
        [_doc("note:title", "Gateway"), _doc("note:body", "Billing", body="gateway")]
    )

    assert _ids(real_engine.query("gateway")) == ["note:title", "note:body"]
    assert _ids(real_engine.query("gateway", kinds=["note"])) == [
        "note:title",
        "note:body",
    ]


def test_an_index_lost_with_its_volume_is_recreated_with_its_settings(
    real_engine, meilisearch_config
):
    real_engine.upsert([_doc("note:1")])
    client = MeilisearchClient(
        meilisearch_config.url,
        meilisearch_config.key,
        request_timeout=10,
        task_timeout=30,
    )
    client.run_task("DELETE", f"/indexes/{meilisearch_config.index}")

    real_engine.upsert([_doc("task:2")])

    assert _ids(real_engine.query("gateway", kinds=["task"])) == ["task:2"]


def test_health_reports_the_document_count(real_engine):
    real_engine.upsert([_doc("note:1"), _doc("note:2")])

    health = real_engine.health()

    assert health.ok
    assert health.document_count == 2
