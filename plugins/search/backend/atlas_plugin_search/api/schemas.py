from datetime import datetime
from typing import Annotated

from atlas_plugin_api import CamelModel
from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    q: str = ""
    kinds: str | None = None
    """Comma-separated document kinds to restrict the search to."""
    page: Annotated[int, Field(ge=1)] = 1
    page_size: Annotated[int, Field(ge=1, le=50)] = 20
    facets: bool = False
    """Also return per-kind counts of the matching documents, regardless of `kinds`."""


class SnippetOut(CamelModel):
    text: str
    matches: list[tuple[int, int]]
    """`[start, end)` character offsets into `text`; slice to highlight."""


class SearchResultOut(CamelModel):
    id: str
    kind: str
    kind_label: str
    title: str
    link: str
    snippet: SnippetOut | None


class KindCountOut(CamelModel):
    kind: str
    kind_label: str
    count: int


class SearchResponse(CamelModel):
    results: list[SearchResultOut]
    total: int
    page: int
    page_size: int
    has_more: bool
    facets: list[KindCountOut] | None = None
    """Present only when requested with `facets=true`."""


class StatusResponse(CamelModel):
    """Limited detail for any authenticated user; the optional fields are
    present for administrators only."""

    ok: bool
    engine_healthy: bool
    pending_count: int
    oldest_pending_age_seconds: int | None
    last_drain_at: datetime | None
    last_rebuild_at: datetime | None
    has_error: bool
    engine: str | None = None
    engine_detail: str | None = None
    document_count: int | None = None
    last_error: str | None = None
    last_error_at: datetime | None = None
    last_error_job: str | None = None
    drain_interval_seconds: int | None = None
    rebuild_interval_seconds: int | None = None
