"""Search and status endpoints.

Every request needs an authenticated session. When the plugin is not active
(not selected is covered by the route not being mounted; a disabled plugin
keeps its app installed) both endpoints answer 404.
"""

from http import HTTPStatus

from atlas_plugin_api import SessionAuth, get_policy_evaluator
from atlas_plugin_api.controllers import AtlasController
from dmr import Query, ResponseSpec, modify
from dmr.errors import ErrorModel, ErrorType, format_error
from dmr.response import APIError

from .. import runtime, service, status
from ..plugin import STATUS_ADMIN_PERMISSION
from ..snippets import utf16_matches
from .schemas import (
    KindCountOut,
    SearchQuery,
    SearchResponse,
    SearchResultOut,
    SnippetOut,
    StatusResponse,
)


def _require_active() -> None:
    if not runtime.is_active():
        raise APIError(
            format_error("Search is not available", error_type=ErrorType.not_found),
            status_code=HTTPStatus.NOT_FOUND,
        )


class SearchController(AtlasController):
    auth = (SessionAuth(),)

    @modify(
        operation_id="search",
        summary="Search the catalog",
        description=(
            "Ranked results for a text query across every registered source, "
            "limited to what the caller may read."
        ),
        extra_responses=[
            ResponseSpec(ErrorModel, status_code=HTTPStatus.NOT_FOUND),
            ResponseSpec(ErrorModel, status_code=HTTPStatus.SERVICE_UNAVAILABLE),
        ],
    )
    def get(self, parsed_query: Query[SearchQuery]) -> SearchResponse:
        _require_active()
        kinds = (
            [kind.strip() for kind in parsed_query.kinds.split(",") if kind.strip()]
            if parsed_query.kinds
            else None
        )
        try:
            page = service.search(
                self.request.user,
                parsed_query.q,
                kinds=kinds,
                page=parsed_query.page,
                page_size=parsed_query.page_size,
                with_facets=parsed_query.facets,
            )
        except service.SearchUnavailableError:
            raise APIError(
                format_error(
                    "The search engine is unavailable",
                    error_type=ErrorType.value_error,
                ),
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            ) from None
        return SearchResponse(
            results=[
                SearchResultOut(
                    id=r.id,
                    kind=r.kind,
                    kind_label=r.kind_label,
                    title=r.title,
                    link=r.link,
                    snippet=(
                        SnippetOut(
                            text=r.snippet.text,
                            matches=utf16_matches(r.snippet.text, r.snippet.matches),
                        )
                        if r.snippet
                        else None
                    ),
                )
                for r in page.results
            ],
            total=page.total,
            page=page.page,
            page_size=page.page_size,
            has_more=page.has_more,
            facets=(
                [
                    KindCountOut(kind=f.kind, kind_label=f.kind_label, count=f.count)
                    for f in page.facets
                ]
                if page.facets is not None
                else None
            ),
        )


class StatusController(AtlasController):
    auth = (SessionAuth(),)

    @modify(
        operation_id="search_status",
        summary="Search index status",
        description=(
            "Engine health and indexing state; operational detail is shown "
            "to administrators only."
        ),
        extra_responses=[ResponseSpec(ErrorModel, status_code=HTTPStatus.NOT_FOUND)],
    )
    def get(self) -> StatusResponse:
        _require_active()
        snap = status.snapshot()
        out = StatusResponse(
            ok=snap.engine_healthy and not snap.has_error,
            engine_healthy=snap.engine_healthy,
            pending_count=snap.pending_count,
            oldest_pending_age_seconds=snap.oldest_pending_age_seconds,
            last_drain_at=snap.last_drain_at,
            last_rebuild_at=snap.last_rebuild_at,
            has_error=snap.has_error,
        )
        if get_policy_evaluator().check(
            self.request.user, STATUS_ADMIN_PERMISSION, None
        ):
            out.engine = snap.engine_id
            out.engine_detail = snap.engine_detail
            out.document_count = snap.document_count
            out.last_error = snap.last_error
            out.last_error_at = snap.last_error_at
            out.last_error_job = snap.last_error_job
            out.drain_interval_seconds = snap.drain_interval_seconds
            out.rebuild_interval_seconds = snap.rebuild_interval_seconds
        return out
