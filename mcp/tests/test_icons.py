from atlas_mcp._gravity_icons import GRAVITY_ICONS
from atlas_mcp.icons import search_flow_icons


def test_search_flow_icons_matches_by_keyword_not_just_literal_name():
    # "CircleExclamation" ships no "error" in its own kebab name, only in
    # its keywords — this is exactly the gap that sent an agent digging
    # through the frontend's source for an icon name instead.
    results = search_flow_icons("attention")

    assert "CircleExclamation" in results


def test_search_flow_icons_matches_any_query_word():
    results = search_flow_icons("totallyunknownword close")

    assert "CircleXmark" in results


def test_search_flow_icons_is_case_insensitive():
    assert search_flow_icons("ATTENTION") == search_flow_icons("attention")


def test_search_flow_icons_respects_limit():
    results = search_flow_icons("", limit=3)

    assert len(results) == 3


def test_search_flow_icons_empty_query_returns_results():
    results = search_flow_icons()

    assert len(results) > 0
    assert all(isinstance(name, str) for name in results)


def test_search_flow_icons_only_returns_known_component_names():
    known_names = {name for name, _ in GRAVITY_ICONS}

    results = search_flow_icons("status", limit=len(GRAVITY_ICONS))

    assert set(results) <= known_names


def test_search_flow_icons_unmatched_query_returns_empty():
    assert search_flow_icons("xyznonexistenticonquery123") == []
