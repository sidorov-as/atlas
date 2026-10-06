"""Snippets: short plain-text excerpts with the query matches located.

A snippet is data, not markup: `text` is plain text and `matches` are
`[start, end)` character offsets into it. A client highlights by slicing the
text, so nothing in an indexed document can inject markup through a snippet.
HTML tags found in the source text are removed on top of that, so the text
is also safe for a client that renders it carelessly.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass

DEFAULT_SNIPPET_CHARS = 180
_ELLIPSIS = "…"
_TAG = re.compile(r"</?[A-Za-z][^>]*>|<!--.*?-->", re.DOTALL)
_WHITESPACE = re.compile(r"\s+")
_TERM = re.compile(r"\w+", re.UNICODE)


@dataclass(frozen=True, slots=True)
class Snippet:
    text: str
    matches: tuple[tuple[int, int], ...] = ()


def clean_text(text: str) -> str:
    """Strip HTML tags and collapse whitespace."""
    return _WHITESPACE.sub(" ", _TAG.sub(" ", text)).strip()


def query_terms(query: str) -> list[str]:
    seen: dict[str, None] = {}
    for term in _TERM.findall(query.lower()):
        seen.setdefault(term)
    return list(seen)


def find_matches(text: str, terms: list[str]) -> list[tuple[int, int]]:
    """Occurrences of any term at the start of a word, in text order."""
    if not terms:
        return []
    pattern = re.compile(
        r"(?<!\w)(?:" + "|".join(re.escape(t) for t in terms) + r")\w*",
        re.IGNORECASE | re.UNICODE,
    )
    return [m.span() for m in pattern.finditer(text)]


def _word_start(text: str, index: int) -> int:
    while index > 0 and not text[index - 1].isspace():
        index -= 1
    return index


def _word_end(text: str, index: int) -> int:
    while index < len(text) and not text[index].isspace():
        index += 1
    return index


def _window(text: str, around: int, width: int) -> tuple[int, int]:
    start = _word_start(text, max(0, around - width // 3))
    end = _word_end(text, min(len(text), start + width))
    return start, end


def _excerpt(text: str, start: int, end: int, terms: list[str]) -> Snippet:
    prefix = _ELLIPSIS if start > 0 else ""
    suffix = _ELLIPSIS if end < len(text) else ""
    body = text[start:end]
    shift = len(prefix)
    matches = tuple((a + shift, b + shift) for a, b in find_matches(body, terms))
    return Snippet(text=f"{prefix}{body}{suffix}", matches=matches)


def build_snippet(
    text: str,
    summary: str | None,
    query: str,
    *,
    width: int = DEFAULT_SNIPPET_CHARS,
) -> Snippet | None:
    """Excerpt of `text` around the first query match.

    When the text has no match (the match was in the title, or the engine
    matched a stemmed form) the snippet is the start of the summary, else of
    the text, with no marked matches. `None` when there is nothing to show.
    """
    terms = query_terms(query)
    body = clean_text(text)
    first = find_matches(body, terms)
    if first:
        start, end = _window(body, first[0][0], width)
        return _excerpt(body, start, end, terms)
    fallback = clean_text(summary) if summary else body
    if not fallback:
        return None
    return _excerpt(fallback, 0, _word_end(fallback, min(len(fallback), width)), terms)


def _valid_matches(
    text: str, matches: Sequence[tuple[int, int]]
) -> tuple[tuple[int, int], ...]:
    """Engine offsets that lie within `text`, in order and without overlap.

    The contract already guarantees this; dropping the rest here means one
    faulty candidate cannot break a response.
    """
    valid = []
    previous_end = 0
    for start, end in matches:
        if previous_end <= start < end <= len(text):
            valid.append((start, end))
            previous_end = end
    return tuple(valid)


def highlight_snippet(
    highlight: str,
    query: str,
    matches: Sequence[tuple[int, int]] = (),
) -> Snippet | None:
    """Snippet from an engine-supplied plain-text highlight.

    With engine `matches` the highlight is used as it is, since cleaning it
    would shift the offsets, and exactly those ranges are marked. Without them
    the highlight is cleaned and the matches are located by the query terms.
    """
    if matches:
        return Snippet(text=highlight, matches=_valid_matches(highlight, matches))
    text = clean_text(highlight)
    if not text:
        return None
    return Snippet(text=text, matches=tuple(find_matches(text, query_terms(query))))


def utf16_matches(
    text: str, matches: Sequence[tuple[int, int]]
) -> list[tuple[int, int]]:
    """Code-point `matches` of `text` as UTF-16 code-unit ranges.

    A character outside the Basic Multilingual Plane is one code point and
    two UTF-16 code units, so each one before an offset moves it by one.
    """
    shifts = [0]
    for char in text:
        shifts.append(shifts[-1] + (ord(char) > 0xFFFF))
    return [(a + shifts[a], b + shifts[b]) for a, b in matches]
