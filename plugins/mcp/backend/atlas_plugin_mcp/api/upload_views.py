"""`request_attach` MCP tool (`mcp-upload-tools` spec): issues a one-time
upload ticket for one field of one entity, so an agent with a shell can send
a large file straight to Atlas instead of passing it through the LLM.

Issuance, scope and RBAC checks live in Core's ticket service
(`atlas_plugin_api.get_upload_ticket_service`); this controller only resolves
the entity reference and maps errors. The raw `PUT` is deliberately not an MCP
operation.

Only mounted when at least one upload target is registered
(`atlas_plugin_mcp.api.urls`).
"""

from http import HTTPStatus

from atlas_plugin_api import (
    FORBIDDEN_RESPONSE,
    PATBearerAuth,
    RefError,
    UnknownUploadTargetError,
    UploadForbiddenError,
    UploadValidationError,
    get_upload_ticket_service,
    resolve_ref,
)
from atlas_plugin_api.controllers import AtlasController
from dmr import Body, ResponseSpec, modify
from dmr.errors import ErrorModel, ErrorType, format_error
from dmr.response import APIError
from dmr.security.base import request_auth

from .schemas import RequestAttachIn, RequestAttachOut

_ENTITY_NOT_FOUND_RESPONSE = ResponseSpec(
    ErrorModel,
    status_code=HTTPStatus.NOT_FOUND,
    description="The entity ref does not resolve",
)


def _error(message: str, error_type: ErrorType, status: HTTPStatus) -> APIError:
    return APIError(format_error(message, error_type=error_type), status_code=status)


class RequestAttachController(AtlasController):
    """The `request_attach` MCP tool."""

    auth = (PATBearerAuth(),)

    @modify(
        operation_id="request_attach",
        summary="Request an upload link",
        description=(
            "Get a one-time URL to upload a large file (an API spec, a "
            "database schema) straight into one field of an existing "
            "entity, without passing its text through this conversation. "
            "Give `entity` as `kind:name`, `field` (e.g. `spec` of an `api`, "
            "`schema` of a `resource`) and any `params`. The caller then "
            "sends the raw file with `PUT` to the URL, e.g. `curl -T file "
            "URL`. The link is a secret, valid for a few minutes, and "
            "accepts one successful upload; a rejected upload (bad content) "
            "may be retried against the same URL until it expires. A "
            "successful upload's `ok` means the content was SAVED; for a "
            "schema, `parse_status` and `parse_error` report separately "
            "whether it parsed. Requires the PAT scope that governs the "
            "target (`apis:write` for an API spec, `catalog:write` for a "
            "schema)."
        ),
        status_code=HTTPStatus.OK,
        extra_responses=[FORBIDDEN_RESPONSE, _ENTITY_NOT_FOUND_RESPONSE],
    )
    def post(self, parsed_body: Body[RequestAttachIn]) -> RequestAttachOut:
        resolved = request_auth(self.request).resolved
        try:
            entity = resolve_ref(parsed_body.entity)
        except RefError as exc:
            raise _error(str(exc), ErrorType.not_found, HTTPStatus.NOT_FOUND) from None

        try:
            issued = get_upload_ticket_service().issue(
                user=self.request.user,
                token_id=resolved.token_id,
                scopes=resolved.scopes,
                entity=entity,
                field=parsed_body.field,
                params=parsed_body.params,
            )
        except UnknownUploadTargetError as exc:
            raise _error(
                str(exc), ErrorType.value_error, HTTPStatus.BAD_REQUEST
            ) from None
        except UploadValidationError as exc:
            raise _error(
                exc.reason, ErrorType.value_error, HTTPStatus.BAD_REQUEST
            ) from None
        except UploadForbiddenError as exc:
            raise _error(exc.reason, ErrorType.security, HTTPStatus.FORBIDDEN) from None

        return RequestAttachOut(
            entity=entity.ref,
            field=parsed_body.field,
            upload_path=issued.path,
            expires_at=issued.expires_at,
            max_bytes=issued.max_bytes,
        )
