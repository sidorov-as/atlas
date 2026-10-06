"""`(api, spec)` upload target (`apis-plugin` spec): applies a raw body as the
API's inline spec content through the same source application the CRUD API and
ingestion use. Endpoint/operation synchronization runs from the `ApiDetails`
`post_save` signal, as for any other write.
"""

from collections.abc import Mapping
from typing import Any

import yaml
from atlas_plugin_api import (
    KIND_API,
    UploadResult,
    UploadTarget,
    UploadValidationError,
)

from atlas_plugin_apis import asyncapi_import, openapi_import
from atlas_plugin_apis.models import ApiDetails, ApiEndpoint, ApiOperation
from atlas_plugin_apis.spec_fetch import (
    MAX_SPEC_RESPONSE_BYTES,
    _within_parse_limits,
    apply_api_spec_source,
)

SPEC_FIELD = "spec"
SPEC_UPLOAD_SCOPE = "apis:write"

_PARSERS = {
    ApiDetails.TYPE_OPENAPI: openapi_import,
    ApiDetails.TYPE_ASYNCAPI: asyncapi_import,
}


def _rejection_reason(details: ApiDetails, text: str) -> str | None:
    """Why `text` cannot become `details`' spec, or `None` if it can: the
    cheap gate `fetch_spec_content` applies to URL specs (non-empty, parses,
    within limits), plus the type's own parser so a document of the wrong
    kind is refused instead of saved and silently left unsynchronized."""
    if not text.strip():
        return "The request body is empty"
    try:
        parsed = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return f"The body is not valid YAML or JSON: {exc}"
    if not _within_parse_limits(parsed):
        return "The document exceeds the size or nesting limits for specs"
    parser = _PARSERS.get(details.type)
    if parser is not None:
        try:
            parser.parse_operations(text, api_label=str(details))
        except parser.SpecParseError as exc:
            return f"Not a usable {details.type} document: {exc}"
    return None


def _synced_count(details: ApiDetails) -> int | None:
    entity = details.entity
    if details.type == ApiDetails.TYPE_OPENAPI:
        return ApiEndpoint.objects.filter(
            api=entity, status=ApiEndpoint.STATUS_ACTIVE
        ).count()
    if details.type == ApiDetails.TYPE_ASYNCAPI:
        return ApiOperation.objects.filter(
            api=entity, status=ApiOperation.STATUS_ACTIVE
        ).count()
    return None


class ApiSpecUploadAdapter:
    def validate_params(self, params: Mapping[str, Any]) -> dict[str, Any]:
        return {}

    def apply(
        self, entity: Any, body: bytes, params: Mapping[str, Any], user: Any
    ) -> UploadResult:
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError:
            msg = "The body is not valid UTF-8"
            raise UploadValidationError(msg) from None

        details = entity.api_details
        reason = _rejection_reason(details, text)
        if reason is not None:
            raise UploadValidationError(reason)

        apply_api_spec_source(details, ApiDetails.SPEC_SOURCE_INLINE, "", text)
        details.save()

        summary: dict[str, Any] = {"spec_kind": details.type}
        count = _synced_count(details)
        if count is not None:
            key = (
                "endpoints" if details.type == ApiDetails.TYPE_OPENAPI else "operations"
            )
            summary[key] = count
        return UploadResult(summary=summary)


def api_spec_upload_target() -> UploadTarget:
    return UploadTarget(
        kind=KIND_API,
        field=SPEC_FIELD,
        required_scope=SPEC_UPLOAD_SCOPE,
        max_bytes=MAX_SPEC_RESPONSE_BYTES,
        adapter=ApiSpecUploadAdapter(),
    )
