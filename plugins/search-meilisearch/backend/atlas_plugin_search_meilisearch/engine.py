"""Meilisearch implementation of the `SearchEngine` contract."""

import json
import logging
import re
import unicodedata
import uuid
from collections.abc import Collection, Iterable
from itertools import batched
from typing import Any

from atlas_plugin_api import (
    EngineCapabilities,
    EngineHealth,
    SearchCandidate,
    SearchDocument,
)

from .client import MeilisearchApiError, MeilisearchClient, MeilisearchError
from .config import SearchMeilisearchPluginConfig
from .ids import encode_id

logger = logging.getLogger(__name__)

BATCH_SIZE = 500
CROP_WORDS = 30
CROP_MARKER = "…"

INDEX_SETTINGS: dict[str, Any] = {
    # Order is the ranking: a title match beats a summary match beats a body match.
    "searchableAttributes": ["title", "summary", "body"],
    "filterableAttributes": ["kind"],
}

# Private-use characters mark matches in the engine's formatted text. They are
# not whitespace and not markup, so cleaning leaves them in place and the
# offsets are read off the cleaned text; the markers themselves never leave
# this module, so nothing from the index can arrive at the UI as markup.
_MATCH_START = ""
_MATCH_END = ""
_TAG = re.compile(r"</?[A-Za-z][^>]*>|<!--.*?-->", re.DOTALL)
_WHITESPACE = re.compile(r"\s+")


def to_highlight(formatted: str) -> tuple[str, tuple[tuple[int, int], ...]]:
    """Engine-formatted text -> plain text and the code-point ranges it matched.

    The text has no match markers or HTML tags and has collapsed whitespace; the
    ranges address that final text and cover whole words. Unbalanced or nested markers (a marker lost
    inside an HTML tag, say) are dropped rather than guessed at.
    """
    cleaned = _WHITESPACE.sub(" ", _TAG.sub(" ", formatted)).strip()
    text: list[str] = []
    matches: list[tuple[int, int]] = []
    start: int | None = None
    for char in cleaned:
        if char == _MATCH_START:
            if start is None:
                start = len(text)
        elif char == _MATCH_END:
            if start is not None:
                matches.append((start, len(text)))
                start = None
        else:
            text.append(char)
    plain = "".join(text)
    spans = [span for m in matches if (span := _trimmed(plain, *m))]
    return plain, _merged([_whole_word(plain, *span) for span in spans])


def _trimmed(text: str, start: int, end: int) -> tuple[int, int] | None:
    """The range without surrounding whitespace, or None when nothing is left."""
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return (start, end) if start < end else None


def _is_unsegmented(char: str) -> bool:
    """Scripts written without spaces: the engine splits them, a word edge cannot."""
    code = ord(char)
    return (
        0x3040 <= code <= 0x30FF  # hiragana, katakana
        or 0x3400 <= code <= 0x9FFF  # CJK ideographs
        or 0xF900 <= code <= 0xFAFF
        or 0x20000 <= code <= 0x2FFFF
        or 0x0E00 <= code <= 0x0E7F  # Thai
    )


def _is_word_char(char: str) -> bool:
    return unicodedata.category(char)[0] in "LNM"


def _same_word(before: str, after: str) -> bool:
    """Whether two neighbouring characters belong to one word.

    The engine ends a word at anything that is not a letter or digit (so at `_`
    and `-`), between a lowercase and an uppercase letter (camelCase), and
    around scripts written without spaces.
    """
    if not (_is_word_char(before) and _is_word_char(after)):
        return False
    if _is_unsegmented(before) or _is_unsegmented(after):
        return False
    return not (before.islower() and after.isupper())


def _whole_word(text: str, start: int, end: int) -> tuple[int, int]:
    """The range grown to the edges of the words it touches.

    The engine marks only the matched part of a word for a typo or a prefix
    (`paymen` of `payment`); a reader expects the whole word marked.
    """
    while start > 0 and _same_word(text[start - 1], text[start]):
        start -= 1
    while end < len(text) and _same_word(text[end - 1], text[end]):
        end += 1
    return start, end


def _merged(spans: list[tuple[int, int]]) -> tuple[tuple[int, int], ...]:
    """Spans in text order with overlapping ones joined."""
    merged: list[tuple[int, int]] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return tuple(merged)


def to_plain_highlight(formatted: str) -> str:
    """Engine-formatted text -> plain text without match markers or HTML tags."""
    return to_highlight(formatted)[0]


class MeilisearchSearchEngine:
    """Keeps the index in a Meilisearch instance."""

    id = "meilisearch"
    capabilities = EngineCapabilities(highlights=True, typo_tolerance=True)

    def __init__(self, config: SearchMeilisearchPluginConfig) -> None:
        key = config.key
        if key is not None and not isinstance(key, str):
            raise ValueError(
                "plugin setting 'key' is an unresolved secret reference; "
                "Core resolves it before the engine starts"
            )
        self._index = config.index
        self._client = MeilisearchClient(
            config.url,
            key,
            request_timeout=config.request_timeout_seconds,
            task_timeout=config.task_timeout_seconds,
        )
        self._configured = False

    def upsert(self, documents: Iterable[SearchDocument]) -> None:
        self._ensure_index()
        for chunk in batched(documents, BATCH_SIZE):
            self._add(self._index, chunk)

    def delete(self, ids: Iterable[str]) -> None:
        self._ensure_index()
        for chunk in batched(ids, BATCH_SIZE):
            self._client.run_task(
                "POST",
                f"/indexes/{self._index}/documents/delete-batch",
                json=[encode_id(document_id) for document_id in chunk],
            )

    def replace_all(self, documents: Iterable[SearchDocument]) -> None:
        """Build a fresh index, swap it with the live one, drop the old one.

        Queries see the old content until the swap and the new content after
        it. A failure while building discards the temporary index and leaves
        the live one untouched.
        """
        self._ensure_index()
        temporary = f"{self._index}-build-{uuid.uuid4().hex[:12]}"
        try:
            self._create_index(temporary)
            for chunk in batched(documents, BATCH_SIZE):
                self._add(temporary, chunk)
            self._client.run_task(
                "POST", "/swap-indexes", json=[{"indexes": [self._index, temporary]}]
            )
        except BaseException:
            self._discard(temporary)
            raise
        # After the swap `temporary` holds the superseded content.
        self._discard(temporary)

    def query(
        self,
        text: str,
        *,
        kinds: Collection[str] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[SearchCandidate]:
        # An empty query makes Meilisearch return every document.
        if not text.strip() or kinds is not None and not kinds:
            return []
        payload: dict[str, Any] = {
            "q": text,
            "limit": limit,
            "offset": offset,
            "showRankingScore": True,
            "attributesToRetrieve": ["document_id"],
            "attributesToHighlight": ["summary", "body"],
            "attributesToCrop": ["summary", "body"],
            "cropLength": CROP_WORDS,
            "cropMarker": CROP_MARKER,
            "highlightPreTag": _MATCH_START,
            "highlightPostTag": _MATCH_END,
        }
        if kinds is not None:
            quoted = ", ".join(json.dumps(kind) for kind in sorted(kinds))
            payload["filter"] = f"kind IN [{quoted}]"
        try:
            result = self._client.request(
                "POST", f"/indexes/{self._index}/search", json=payload
            )
        except MeilisearchApiError as exc:
            if exc.code == "index_not_found":
                return []
            raise
        return [self._candidate(hit) for hit in result["hits"]]

    def health(self) -> EngineHealth:
        try:
            self._client.request("GET", "/health")
            try:
                stats = self._client.request("GET", f"/indexes/{self._index}/stats")
            except MeilisearchApiError as exc:
                if exc.code != "index_not_found":
                    raise
                return EngineHealth(ok=True, document_count=0)
        except MeilisearchError as exc:
            return EngineHealth(ok=False, detail=str(exc))
        return EngineHealth(ok=True, document_count=stats["numberOfDocuments"])

    def _candidate(self, hit: dict[str, Any]) -> SearchCandidate:
        formatted = hit.get("_formatted") or {}
        highlight, matches = None, ()
        for field in ("body", "summary"):
            value = formatted.get(field)
            if isinstance(value, str) and _MATCH_START in value:
                highlight, matches = to_highlight(value)
                break
        return SearchCandidate(
            id=hit["document_id"],
            score=float(hit.get("_rankingScore", 0.0)),
            highlight=highlight or None,
            highlight_matches=matches if highlight else (),
        )

    def _add(self, index: str, chunk: tuple[SearchDocument, ...]) -> None:
        # One request cannot carry the same id twice: the last duplicate wins.
        latest = {document.id: document for document in chunk}
        self._client.run_task(
            "POST",
            f"/indexes/{index}/documents?primaryKey=id",
            json=[self._payload(document) for document in latest.values()],
        )

    @staticmethod
    def _payload(document: SearchDocument) -> dict[str, Any]:
        return {
            "id": encode_id(document.id),
            "document_id": document.id,
            "kind": document.kind,
            "title": document.title,
            "summary": document.summary or "",
            "body": document.body,
            "route": document.route,
        }

    def _ensure_index(self) -> None:
        """Create the live index when it is missing and apply its settings.

        Checked on every write so an index lost with its volume is rebuilt
        with the right settings instead of being created implicitly without
        them; the settings themselves are re-applied once per process.
        """
        try:
            self._client.request("GET", f"/indexes/{self._index}")
        except MeilisearchApiError as exc:
            if exc.code != "index_not_found":
                raise
            self._create_index(self._index, configure=False)
            self._configured = False
        if not self._configured:
            self._apply_settings(self._index)
            self._configured = True

    def _create_index(self, index: str, *, configure: bool = True) -> None:
        try:
            self._client.run_task(
                "POST", "/indexes", json={"uid": index, "primaryKey": "id"}
            )
        except MeilisearchError as exc:
            # Another process created it between the check and this call.
            if getattr(exc, "code", None) != "index_already_exists":
                raise
        if configure:
            self._apply_settings(index)

    def _apply_settings(self, index: str) -> None:
        self._client.run_task(
            "PATCH", f"/indexes/{index}/settings", json=INDEX_SETTINGS
        )

    def _discard(self, index: str) -> None:
        try:
            self._client.run_task("DELETE", f"/indexes/{index}")
        except MeilisearchError:
            logger.warning(
                "Could not delete temporary Meilisearch index %s", index, exc_info=True
            )
