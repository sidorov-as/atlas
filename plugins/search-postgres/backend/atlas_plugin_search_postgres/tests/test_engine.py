import pytest
from atlas_plugin_api import SearchDocument
from django.db import connection, transaction

from atlas_plugin_search_postgres.engine import PostgresSearchEngine
from atlas_plugin_search_postgres.models import SearchIndexEntry

pytestmark = pytest.mark.django_db


def doc(key, title, body="", kind="note"):
    return SearchDocument(id=f"{kind}:{key}", kind=kind, title=title, body=body)


def ids(candidates):
    return [c.id for c in candidates]


@pytest.fixture
def engine():
    return PostgresSearchEngine()


def test_declares_no_highlights(engine):
    assert engine.capabilities.highlights is False


def test_title_match_outranks_body_match_even_with_a_repeated_body_term(engine):
    engine.upsert(
        [
            doc("body", "Billing", "gateway gateway gateway gateway gateway"),
            doc("title", "Gateway", "routes requests"),
        ]
    )

    candidates = engine.query("gateway")

    assert ids(candidates) == ["note:title", "note:body"]
    assert candidates[0].score > candidates[1].score


def test_all_terms_must_match(engine):
    engine.upsert(
        [
            doc("both", "Payment gateway"),
            doc("one", "Payment service"),
            doc("split", "Gateway", "handles payment"),
        ]
    )

    assert sorted(ids(engine.query("payment gateway"))) == [
        "note:both",
        "note:split",
    ]


@pytest.mark.parametrize(
    "text",
    ["'", '"', "&", "|", "!", ":*", "(", ")", "a & | b", "\\", "<->", "gateway:*'"],
)
def test_operators_are_plain_text(engine, text):
    engine.upsert([doc("1", "Gateway")])

    engine.query(text)


def test_operators_do_not_change_matching(engine):
    engine.upsert([doc("1", "Gateway"), doc("2", "Billing")])

    assert ids(engine.query("gateway | billing")) == []
    assert ids(engine.query("!gateway")) == ["note:1"]


def test_blank_query_matches_nothing(engine):
    engine.upsert([doc("1", "Gateway")])

    assert engine.query("   ") == []


def test_query_uses_the_gin_index(engine):
    engine.upsert([doc(str(i), f"Service {i}") for i in range(20)])
    with transaction.atomic(), connection.cursor() as cursor:
        # The planner rightly prefers a scan on a tiny table: forbid it so
        # the plan shows whether the query *can* use the index.
        cursor.execute("SET LOCAL enable_seqscan = off")
        cursor.execute(
            "EXPLAIN SELECT document_id FROM search_postgres_searchindexentry "
            "WHERE search_vector @@ plainto_tsquery('simple', 'service')"
        )
        plan = "\n".join(row[0] for row in cursor.fetchall())

    assert "search_pg_vector_gin" in plan


def test_upsert_with_duplicate_ids_in_one_batch_keeps_the_last(engine):
    engine.upsert([doc("1", "Alpha"), doc("1", "Beta")])

    assert ids(engine.query("alpha")) == []
    assert ids(engine.query("beta")) == ["note:1"]
    assert SearchIndexEntry.objects.count() == 1


def test_upsert_spans_several_batches(engine, monkeypatch):
    monkeypatch.setattr("atlas_plugin_search_postgres.engine.BATCH_SIZE", 2)

    engine.upsert(doc(str(i), "Gateway") for i in range(5))

    assert SearchIndexEntry.objects.count() == 5


def test_delete_spans_several_batches(engine, monkeypatch):
    monkeypatch.setattr("atlas_plugin_search_postgres.engine.BATCH_SIZE", 2)
    engine.upsert(doc(str(i), "Gateway") for i in range(5))

    engine.delete(f"note:{i}" for i in range(5))

    assert SearchIndexEntry.objects.count() == 0


def test_replace_all_keeps_kind_filter_working(engine):
    engine.upsert([doc("old", "Gateway")])

    engine.replace_all([doc("1", "Gateway", kind="task")])

    assert ids(engine.query("gateway", kinds=["task"])) == ["task:1"]
    assert engine.query("gateway", kinds=["note"]) == []


def test_failed_replace_all_leaves_the_stored_rows_untouched(engine):
    engine.upsert([doc("1", "Old gateway")])

    def broken():
        yield doc("2", "New gateway")
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        engine.replace_all(broken())

    assert list(SearchIndexEntry.objects.values_list("document_id", flat=True)) == [
        "note:1"
    ]


def test_text_search_config_applies_stemming(db):
    stemming = PostgresSearchEngine("english")
    stemming.replace_all([doc("1", "Payments")])
    assert ids(stemming.query("payment")) == ["note:1"]

    plain = PostgresSearchEngine("simple")
    plain.replace_all([doc("1", "Payments")])
    assert ids(plain.query("payment")) == []
    assert ids(plain.query("payments")) == ["note:1"]


def test_health_reports_the_document_count(engine):
    engine.upsert([doc("1", "Gateway"), doc("2", "Billing")])

    health = engine.health()

    assert health.ok
    assert health.document_count == 2
