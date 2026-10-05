"""Contract tests for the engine-neutral search surface."""

import logging
import subprocess
import sys

import pytest

import atlas_plugin_api.search as search_module
from atlas_plugin_api import (
    DuplicateSearchEngineError,
    DuplicateSearchSourceError,
    EngineCapabilities,
    EngineHealth,
    InvalidSearchSourceError,
    SearchCandidate,
    SearchDocument,
    SearchEngineRegistry,
    SearchEngineSelectionError,
    SearchHit,
    SearchSourceRegistry,
    configure_search_body_limit,
    get_search_engine_lookup,
    get_search_source_lookup,
    register_search_engine,
    register_search_source,
    select_search_engine,
    truncate_body,
)


class _Source:
    def __init__(self, source_id="notes", kinds=("note",)):
        self.id = source_id
        self.kinds = kinds
        self.watched_models = ("notes.Note",)

    def document_ids_for_instance(self, instance):
        return [f"note:{instance}"]

    def documents(self, ids):
        return []

    def all_documents(self):
        return iter(())

    def resolve(self, ids, actor):
        return []


class _Engine:
    capabilities = EngineCapabilities()

    def __init__(self, engine_id="fake"):
        self.id = engine_id

    def upsert(self, documents): ...

    def delete(self, ids): ...

    def replace_all(self, documents): ...

    def query(self, text, *, kinds=None, limit=20, offset=0):
        return []

    def health(self):
        return EngineHealth(ok=True)


@pytest.fixture(autouse=True)
def _restore_body_limit():
    yield
    configure_search_body_limit(None)


def test_document_id_must_be_kind_and_key_with_matching_kind():
    SearchDocument(id="note:1", kind="note", title="t")
    for bad in ("note", "note:", ":1", "task:1"):
        with pytest.raises(ValueError):
            SearchDocument(id=bad, kind="note", title="t")


def test_hit_and_candidate_validate_ids():
    SearchHit(id="note:1", kind="note", title="t", link="/n/1")
    with pytest.raises(ValueError):
        SearchHit(id="task:1", kind="note", title="t", link="/n/1")
    with pytest.raises(ValueError):
        SearchCandidate(id="nokey", score=1.0)


def test_oversized_body_is_truncated_at_word_boundary_with_warning(caplog):
    configure_search_body_limit(20)
    with caplog.at_level(logging.WARNING, logger=search_module.__name__):
        doc = SearchDocument(
            id="note:1", kind="note", title="t", body="alpha beta gamma delta"
        )
    assert doc.body == "alpha beta gamma"
    assert "note:1" in caplog.text


def test_body_within_bound_is_untouched_and_source_may_truncate_earlier(caplog):
    configure_search_body_limit(100)
    with caplog.at_level(logging.WARNING, logger=search_module.__name__):
        doc = SearchDocument(id="note:1", kind="note", title="t", body="short text")
    assert doc.body == "short text"
    assert caplog.text == ""


def test_truncate_body_edge_cases():
    assert truncate_body("alpha beta", 5) == "alpha"
    assert truncate_body("alpha beta", 6) == "alpha"
    assert truncate_body("alphabetagamma", 5) == "alpha"
    assert truncate_body("alpha", 5) == "alpha"


def test_body_limit_must_be_positive():
    with pytest.raises(ValueError):
        configure_search_body_limit(0)


def test_source_registry_rejects_duplicate_id_and_duplicate_kind():
    registry = SearchSourceRegistry()
    registry.register(_Source(), owner="one")
    with pytest.raises(DuplicateSearchSourceError) as same_id:
        registry.register(_Source(kinds=("other",)), owner="two")
    assert same_id.value.existing_owner == "one"
    assert same_id.value.new_owner == "two"
    with pytest.raises(DuplicateSearchSourceError) as same_kind:
        registry.register(_Source("tasks", kinds=("note",)), owner="three")
    assert same_kind.value.value == "note"
    assert registry.for_kind("note").id == "notes"
    assert registry.get("tasks") is None


def test_source_registry_rejects_invalid_sources():
    registry = SearchSourceRegistry()
    with pytest.raises(InvalidSearchSourceError):
        registry.register(object())
    with pytest.raises(InvalidSearchSourceError):
        registry.register(_Source(kinds=()))


def test_engine_registry_rejects_duplicates_and_invalid_engines():
    registry = SearchEngineRegistry()
    registry.register(_Engine(), owner="one")
    with pytest.raises(DuplicateSearchEngineError):
        registry.register(_Engine(), owner="two")
    with pytest.raises(InvalidSearchSourceError):
        registry.register(object())
    assert [e.id for e in registry.all()] == ["fake"]


def test_public_registration_with_no_consumer_is_harmless():
    registry = search_module._search_source_registry
    snapshot = (
        dict(registry._sources),
        dict(registry._owners),
        dict(registry._kind_sources),
    )
    engines = search_module._search_engine_registry
    engine_snapshot = dict(engines._engines), dict(engines._owners)
    try:
        register_search_source(_Source("probe", ("probe",)), owner="test")
        register_search_engine(_Engine("probe"), owner="test")
        assert get_search_source_lookup().get("probe") is not None
        assert get_search_engine_lookup().get("probe") is not None
        assert not hasattr(get_search_source_lookup(), "register")
    finally:
        registry._sources, registry._owners, registry._kind_sources = snapshot
        engines._engines, engines._owners = engine_snapshot


def test_importing_the_api_pulls_in_no_engine_client():
    code = (
        "import sys, atlas_plugin_api;"
        "bad=[m for m in sys.modules if m.split('.')[0] in "
        "('meilisearch','elasticsearch','opensearchpy','typesense','psycopg','psycopg2')];"
        "print(bad)"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert out.stdout.strip() == "[]"


def _engines(*owned):
    registry = SearchEngineRegistry()
    for engine_id, owner in owned:
        registry.register(_Engine(engine_id), owner=owner)
    return registry


def test_selection_fails_when_no_engine_is_registered():
    with pytest.raises(SearchEngineSelectionError, match="engine plugin"):
        select_search_engine(_engines())
    with pytest.raises(SearchEngineSelectionError, match="engine plugin"):
        select_search_engine(_engines(), "atlas.search-postgres")


def test_selection_uses_the_sole_engine_without_a_setting():
    registry = _engines(("pg", "atlas.search-postgres"))
    assert select_search_engine(registry).id == "pg"


def test_selection_accepts_a_setting_naming_the_sole_engines_plugin():
    registry = _engines(("pg", "atlas.search-postgres"))
    assert select_search_engine(registry, "atlas.search-postgres").id == "pg"


def test_selection_rejects_a_setting_naming_another_plugin_than_the_sole_engine():
    registry = _engines(("pg", "atlas.search-postgres"))
    with pytest.raises(SearchEngineSelectionError) as excinfo:
        select_search_engine(registry, "atlas.search-other")
    message = str(excinfo.value)
    assert "atlas.search-other" in message
    assert "atlas.search-postgres" in message


def test_selection_with_two_engines_requires_the_setting_and_lists_both():
    registry = _engines(
        ("pg", "atlas.search-postgres"), ("meili", "atlas.search-meili")
    )
    with pytest.raises(SearchEngineSelectionError) as excinfo:
        select_search_engine(registry)
    message = str(excinfo.value)
    assert "'pg'" in message and "'meili'" in message
    assert "'engine' setting" in message


def test_selection_with_two_engines_uses_the_one_named_by_the_setting():
    registry = _engines(
        ("pg", "atlas.search-postgres"), ("meili", "atlas.search-meili")
    )
    assert select_search_engine(registry, "atlas.search-meili").id == "meili"


def test_selection_rejects_a_setting_matching_no_registered_owner_among_several():
    registry = _engines(
        ("pg", "atlas.search-postgres"), ("meili", "atlas.search-meili")
    )
    with pytest.raises(SearchEngineSelectionError, match="atlas.search-x"):
        select_search_engine(registry, "atlas.search-x")


def test_selection_rejects_a_plugin_registering_several_engines():
    registry = _engines(("a", "atlas.search-postgres"), ("b", "atlas.search-postgres"))
    with pytest.raises(SearchEngineSelectionError, match="several search engines"):
        select_search_engine(registry, "atlas.search-postgres")


def test_selection_works_through_the_public_read_view():
    # Engine registered without an owner never matches a setting.
    registry = _engines(("pg", None))
    assert select_search_engine(registry).id == "pg"
    with pytest.raises(SearchEngineSelectionError):
        select_search_engine(registry, "atlas.search-postgres")
