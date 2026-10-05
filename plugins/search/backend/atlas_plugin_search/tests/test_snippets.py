from atlas_plugin_search.snippets import (
    build_snippet,
    clean_text,
    highlight_snippet,
    query_terms,
)


def _marked(snippet):
    return [snippet.text[a:b] for a, b in snippet.matches]


def test_snippet_surrounds_the_first_match_and_marks_it():
    body = (
        ("lorem ipsum " * 30) + "the payment gateway settles daily " + ("dolor " * 30)
    )

    snippet = build_snippet(body, None, "payment")

    assert "payment gateway" in snippet.text
    assert _marked(snippet) == ["payment"]
    assert snippet.text.startswith("…")
    assert snippet.text.endswith("…")
    assert len(snippet.text) < len(body)


def test_snippet_marks_every_term_and_matches_case_insensitively():
    snippet = build_snippet("Payments and Gateway notes", None, "payment gateway")

    assert _marked(snippet) == ["Payments", "Gateway"]


def test_match_only_in_title_falls_back_to_summary():
    snippet = build_snippet("unrelated body", "short summary text", "payment")

    assert snippet.text == "short summary text"
    assert snippet.matches == ()


def test_match_only_in_title_falls_back_to_start_of_body():
    snippet = build_snippet("unrelated body text", None, "payment")

    assert snippet.text == "unrelated body text"


def test_no_text_means_no_snippet():
    assert build_snippet("", None, "payment") is None
    assert build_snippet("   ", "  ", "payment") is None


def test_html_tags_are_removed_from_snippets():
    body = (
        "see <script>alert(1)</script> the <b>payment</b> gateway <img src=x onerror=y>"
    )

    snippet = build_snippet(body, None, "payment")

    assert "<" not in snippet.text
    assert "payment" in _marked(snippet)


def test_markdown_markup_is_kept_as_inert_text():
    snippet = build_snippet(
        "# Title\n[link](javascript:alert(1)) payment", None, "payment"
    )

    assert "payment" in _marked(snippet)
    assert "\n" not in snippet.text


def test_clean_text_collapses_whitespace():
    assert clean_text("a \n\t b  <br/> c") == "a b c"


def test_query_terms_are_unique_lowercase_words():
    assert query_terms("Pay, pay-ment PAY") == ["pay", "ment"]


def test_engine_highlight_is_used_verbatim_apart_from_cleaning():
    snippet = highlight_snippet("a <em>payment</em> gateway", "payment")

    assert snippet.text == "a payment gateway"
    assert _marked(snippet) == ["payment"]
    assert highlight_snippet("   ", "payment") is None
