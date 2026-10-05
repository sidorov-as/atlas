"""OpenAPI (3.x) / Swagger (2.0) parsing into intermediate operation records
a hand-rolled walker over the
already-`yaml.safe_load`-parsed spec dict, not a new OpenAPI object-model
dependency. Produces exactly the shapes `api/schemas.py`'s
`EndpointRequestOut`/`EndpointResponseOut`/`EndpointSchemaOut` already
contract for, so the upsert layer can write `ParsedOperation.request`/
`.responses` straight into `ApiEndpoint.request`/`.responses`.

A parameter/request-body/response schema that is or contains a `$ref` is
resolved against `components.schemas` (3.x) / `definitions` (Swagger 2.0) via
the shared `spec_refs.resolve_schema`, recursively, with sibling keys next to a `$ref` merged onto the resolved
result (`merge_siblings=True`, uniformly for 3.0/3.1/Swagger 2.0 — Decision
7) instead of being stored verbatim.
"""

import logging
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

import yaml
from django.db import transaction
from django.utils import timezone

from atlas_plugin_apis import spec_refs
from atlas_plugin_apis.models import ApiDetails, ApiEndpoint

logger = logging.getLogger("atlas_plugin_apis")

VERSION_3X = "openapi3"
VERSION_2_0 = "swagger2"

# Matches `ApiEndpoint.METHOD_CHOICES` — a path item's `trace` (3.x-only) and
# any other non-method key (`parameters`, `summary`, `$ref`, `servers`, ...)
# is not a method Atlas models, so it's skipped rather than mapped.
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}

# Matches `EndpointParameterLocation` — `in: cookie` (3.x only) has no
# variant to map to, so it's dropped without failing the operation.
PARAMETER_LOCATIONS = {"path", "query", "header"}

# Keys a Swagger 2.0 non-body parameter carries its schema in directly
# (there's no nested `schema` object outside `in: body`).
_INLINE_SCHEMA_KEYS = {"type", "format", "items", "enum", "default", "nullable", "$ref"}

DEFAULT_BODY_CONTENT_TYPE = "application/json"


class SpecParseError(Exception):
    """`spec_content` has no recognizable version key or no usable `paths`."""


@dataclass
class ParsedOperation:
    """One `(method, path)` operation, normalized to the shape the upsert
    writes into `ApiEndpoint`."""

    method: str
    path: str
    operation_id: str = ""
    summary: str = ""
    description: str = ""
    deprecated: bool = False
    tags: list[str] = field(default_factory=list)
    request: dict[str, Any] = field(default_factory=dict)
    responses: list[dict[str, Any]] = field(default_factory=list)
    external_docs: dict[str, str] = field(default_factory=dict)
    security: list[dict[str, Any]] = field(default_factory=list)


def detect_spec_version(spec_content: str) -> str | None:
    """Load `spec_content` and report which of `openapi: "3.x"` /
    `swagger: "2.0"` / neither it declares itself as."""
    try:
        spec = yaml.safe_load(spec_content)
    except yaml.YAMLError:
        return None
    return _version_of(spec)


def _version_of(spec: Any) -> str | None:
    if not isinstance(spec, dict):
        return None
    openapi_version = spec.get("openapi")
    if isinstance(openapi_version, str) and openapi_version.startswith("3."):
        return VERSION_3X
    if spec.get("swagger") == "2.0":
        return VERSION_2_0
    return None


def parse_operations(
    spec_content: str, *, api_label: str = ""
) -> list[ParsedOperation]:
    """Parse `spec_content` into intermediate operation records.

    Raises `SpecParseError` for a spec-level failure (invalid YAML/JSON, no
    recognizable version key, no usable `paths`) — callers treat that as
    a whole-sync failure. A single operation that doesn't map cleanly is
    logged and skipped instead of aborting the rest of the parse.
    `api_label`, when given, is included in that per-operation log line.
    """
    try:
        spec = yaml.safe_load(spec_content)
    except yaml.YAMLError as exc:
        raise SpecParseError("spec_content is not valid YAML/JSON") from exc

    version = _version_of(spec)
    if version is None:
        raise SpecParseError(
            "spec_content has no recognizable openapi/swagger version key"
        )

    paths = spec.get("paths")
    if not isinstance(paths, dict):
        raise SpecParseError("spec_content has no usable paths")

    doc_consumes = spec.get("consumes") if version == VERSION_2_0 else None
    doc_produces = spec.get("produces") if version == VERSION_2_0 else None

    operations: list[ParsedOperation] = []
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        shared_parameters = path_item.get("parameters")
        shared_parameters = (
            shared_parameters if isinstance(shared_parameters, list) else []
        )

        for method, operation in path_item.items():
            method_lower = method.lower() if isinstance(method, str) else ""
            if method_lower not in HTTP_METHODS or not isinstance(operation, dict):
                continue
            try:
                operations.append(
                    _parse_operation(
                        version=version,
                        method=method_lower.upper(),
                        path=path,
                        operation=operation,
                        shared_parameters=shared_parameters,
                        doc_consumes=doc_consumes,
                        doc_produces=doc_produces,
                        spec=spec,
                    )
                )
            except Exception:
                logger.warning(
                    "Skipping malformed OpenAPI operation %s %s%s",
                    method_lower.upper(),
                    path,
                    f" on {api_label}" if api_label else "",
                    exc_info=True,
                )

    return operations


def _parse_operation(
    *,
    version: str,
    method: str,
    path: str,
    operation: dict,
    shared_parameters: list,
    doc_consumes: list | None,
    doc_produces: list | None,
    spec: dict,
) -> ParsedOperation:
    parameters = [*shared_parameters, *(operation.get("parameters") or [])]
    location_params, body_param, form_params = _split_parameters(parameters)

    request: dict[str, Any] = {}
    mapped_parameters = _map_parameters(location_params, spec)
    if mapped_parameters:
        request["parameters"] = mapped_parameters

    body = None
    if version == VERSION_3X:
        body = _map_request_body_3x(operation.get("requestBody"), spec)
    else:
        consumes = operation.get("consumes", doc_consumes)
        if body_param is not None:
            body = _map_body_parameter_2x(body_param, consumes, spec)
        elif form_params:
            body = _map_form_data_2x(form_params, consumes, spec)
    if body is not None:
        request["body"] = body

    if version == VERSION_3X:
        responses = _map_responses_3x(operation.get("responses") or {}, spec)
    else:
        produces = operation.get("produces", doc_produces)
        responses = _map_responses_2x(operation.get("responses") or {}, produces, spec)

    return ParsedOperation(
        method=method,
        path=path,
        operation_id=operation.get("operationId") or "",
        summary=operation.get("summary") or "",
        description=operation.get("description") or "",
        deprecated=bool(operation.get("deprecated", False)),
        tags=list(operation.get("tags") or []),
        request=request,
        responses=responses,
        external_docs=_extract_external_docs(operation.get("externalDocs")),
        security=_resolve_security(version, operation, spec),
    )


def _split_parameters(parameters: list) -> tuple[list[dict], dict | None, list[dict]]:
    """Split raw parameters into (path/query/header, `in: body`, `in: formData`)
    — `in: cookie` and any unrecognized `in` are dropped."""
    location_params = []
    body_param = None
    form_params = []
    for param in parameters:
        if not isinstance(param, dict):
            continue
        location = param.get("in")
        if location in PARAMETER_LOCATIONS:
            location_params.append(param)
        elif location == "body":
            body_param = param
        elif location == "formData":
            form_params.append(param)
    return location_params, body_param, form_params


def _map_parameters(parameters: list[dict], spec: dict) -> list[dict]:
    mapped = []
    for param in parameters:
        name = param.get("name")
        location = param.get("in")
        if not name or location not in PARAMETER_LOCATIONS:
            continue
        schema = _inline_schema(param)
        mapped.append(
            {
                "name": name,
                "location": location,
                "required": bool(param.get("required", False)),
                "description": param.get("description") or "",
                "schema": spec_refs.resolve_schema(schema, spec, merge_siblings=True)
                if schema is not None
                else None,
            }
        )
    return mapped


def _inline_schema(param: dict) -> dict | None:
    """A parameter's schema — 3.x nests it under `schema`; 2.0 non-body
    parameters carry schema keys directly on the parameter object."""
    schema = param.get("schema")
    if isinstance(schema, dict):
        return schema
    inline = {key: param[key] for key in _INLINE_SCHEMA_KEYS if key in param}
    return inline or None


def _first_or_default(values: list | None, default: str) -> str:
    if isinstance(values, list) and values:
        return values[0]
    return default


def _map_request_body_3x(request_body: Any, spec: dict) -> dict | None:
    if not isinstance(request_body, dict):
        return None
    content = request_body.get("content")
    media, content_type = _pick_media_type(content)
    if media is None:
        return None
    schema = media.get("schema")
    return {
        "content_type": content_type,
        "schema": spec_refs.resolve_schema(schema, spec, merge_siblings=True)
        if schema is not None
        else None,
        "example": media.get("example"),
    }


def _map_body_parameter_2x(body_param: dict, consumes: list | None, spec: dict) -> dict:
    schema = body_param.get("schema")
    return {
        "content_type": _first_or_default(consumes, DEFAULT_BODY_CONTENT_TYPE),
        "schema": spec_refs.resolve_schema(schema, spec, merge_siblings=True)
        if schema is not None
        else None,
        "example": None,
    }


def _map_form_data_2x(
    form_params: list[dict], consumes: list | None, spec: dict
) -> dict:
    properties = {}
    required = []
    for param in form_params:
        name = param.get("name")
        if not name:
            continue
        properties[name] = _inline_schema(param) or {"type": "string"}
        if param.get("required"):
            required.append(name)

    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required

    return {
        "content_type": _first_or_default(consumes, DEFAULT_BODY_CONTENT_TYPE),
        "schema": spec_refs.resolve_schema(schema, spec, merge_siblings=True),
        "example": None,
    }


def _pick_media_type(content: Any) -> tuple[dict | None, str]:
    """Pick a `content[contentType]` media-type object, preferring
    `application/json` when multiple content types are offered."""
    if not isinstance(content, dict) or not content:
        return None, ""
    content_type = (
        DEFAULT_BODY_CONTENT_TYPE
        if DEFAULT_BODY_CONTENT_TYPE in content
        else next(iter(content))
    )
    media = content.get(content_type)
    if not isinstance(media, dict):
        return None, ""
    return media, content_type


def _map_responses_3x(responses: dict, spec: dict) -> list[dict]:
    mapped = []
    for status_code, response in responses.items():
        if not isinstance(response, dict):
            continue
        entry: dict[str, Any] = {
            "status_code": str(status_code),
            "description": response.get("description") or "",
        }
        media, content_type = _pick_media_type(response.get("content"))
        if media is not None:
            schema = media.get("schema")
            entry["content_type"] = content_type
            entry["schema"] = (
                spec_refs.resolve_schema(schema, spec, merge_siblings=True)
                if schema is not None
                else None
            )
            entry["example"] = media.get("example")
        headers = _map_response_headers_3x(response.get("headers"), spec)
        if headers:
            entry["headers"] = headers
        mapped.append(entry)
    return mapped


def _map_responses_2x(responses: dict, produces: list | None, spec: dict) -> list[dict]:
    content_type = _first_or_default(produces, DEFAULT_BODY_CONTENT_TYPE)
    mapped = []
    for status_code, response in responses.items():
        if not isinstance(response, dict):
            continue
        entry: dict[str, Any] = {
            "status_code": str(status_code),
            "description": response.get("description") or "",
        }
        schema = response.get("schema")
        if schema is not None:
            entry["content_type"] = content_type
            entry["schema"] = spec_refs.resolve_schema(
                schema, spec, merge_siblings=True
            )
        headers = _map_response_headers_2x(response.get("headers"), spec)
        if headers:
            entry["headers"] = headers
        mapped.append(entry)
    return mapped


def _map_response_headers_3x(headers: Any, spec: dict) -> dict[str, dict]:
    """A 3.x response's `headers` map — each Header Object nests its type
    under `schema`, same as a Parameter Object."""
    if not isinstance(headers, dict):
        return {}
    mapped = {}
    for name, header in headers.items():
        if not isinstance(header, dict):
            continue
        schema = header.get("schema")
        mapped[name] = {
            "description": header.get("description") or "",
            "schema": spec_refs.resolve_schema(schema, spec, merge_siblings=True)
            if schema is not None
            else None,
        }
    return mapped


def _map_response_headers_2x(headers: Any, spec: dict) -> dict[str, dict]:
    """A 2.0 response's `headers` map — each Header Object carries its type
    keys directly, same as a non-body Parameter Object (`_inline_schema`)."""
    if not isinstance(headers, dict):
        return {}
    mapped = {}
    for name, header in headers.items():
        if not isinstance(header, dict):
            continue
        schema = _inline_schema(header)
        mapped[name] = {
            "description": header.get("description") or "",
            "schema": spec_refs.resolve_schema(schema, spec, merge_siblings=True)
            if schema is not None
            else None,
        }
    return mapped


def _extract_external_docs(external_docs: Any) -> dict[str, str]:
    """An operation's `externalDocs` (`{description?, url}`, identical shape
    in 3.x and 2.0), mirroring `asyncapi_import._extract_external_docs`. Only
    stored when a non-empty `url` is present; missing or url-less
    `externalDocs` yields `{}`, same as a missing field."""
    if not isinstance(external_docs, dict):
        return {}
    url = external_docs.get("url")
    if not url:
        return {}
    return {"description": external_docs.get("description") or "", "url": url}


def _security_schemes(version: str, spec: dict) -> dict:
    if version == VERSION_3X:
        components = spec.get("components")
        schemes = (
            components.get("securitySchemes") if isinstance(components, dict) else None
        )
    else:
        schemes = spec.get("securityDefinitions")
    return schemes if isinstance(schemes, dict) else {}


def _resolve_security(
    version: str, operation: dict, spec: dict
) -> list[dict[str, Any]]:
    """Resolve the operation's effective `security` requirement — its own,
    falling back to the document-level requirement when the operation has no
    `security` key of its own — against
    `components.securitySchemes` (3.x) / `securityDefinitions` (2.0). A
    requirement referencing an unknown scheme name is dropped, not failed."""
    effective_security = operation.get("security")
    if effective_security is None:
        effective_security = spec.get("security")
    if not isinstance(effective_security, list):
        return []

    schemes = _security_schemes(version, spec)
    resolved: list[dict[str, Any]] = []
    seen: set[tuple[str, str | None]] = set()
    for requirement in effective_security:
        if not isinstance(requirement, dict):
            continue
        for scheme_name in requirement:
            scheme = schemes.get(scheme_name)
            if not isinstance(scheme, dict):
                continue
            scheme_type = scheme.get("type")
            if not scheme_type:
                continue
            entry = {
                "type": scheme_type,
                "scheme": scheme.get("scheme") if scheme_type == "http" else None,
            }
            key = (entry["type"], entry["scheme"])
            if key in seen:
                continue
            seen.add(key)
            resolved.append(entry)
    return resolved


def _resolve_servers(spec: dict, version: str) -> tuple[str, str]:
    """Resolve the document's `servers` (3.x) / `host`+`basePath`+`schemes`
    (2.0) into a base URL + protocol, only when unambiguous — mirrors `asyncapi_import._resolve_protocol_2x`'s "resolve
    only when exactly one candidate" rule. Returns `('', '')` for anything
    ambiguous or absent, never a guess among candidates."""
    if version == VERSION_3X:
        return _resolve_servers_3x(spec)
    return _resolve_servers_2x(spec)


def _resolve_servers_3x(spec: dict) -> tuple[str, str]:
    servers = spec.get("servers")
    if not isinstance(servers, list) or len(servers) != 1:
        return "", ""
    server = servers[0]
    if not isinstance(server, dict):
        return "", ""
    url = server.get("url")
    if not isinstance(url, str) or not url:
        return "", ""
    return url, urlsplit(url).scheme


def _resolve_servers_2x(spec: dict) -> tuple[str, str]:
    """The base URL (`host`+`basePath`) resolves independently of `schemes`
    — it's scheme-agnostic by construction — so it may resolve even when
    `schemes` has more than one entry and the protocol is left unresolved."""
    host = spec.get("host")
    if not isinstance(host, str) or not host:
        return "", ""
    base_url = f"{host}{spec.get('basePath') or ''}"
    schemes = spec.get("schemes")
    protocol = schemes[0] if isinstance(schemes, list) and len(schemes) == 1 else ""
    return base_url, protocol


# Fields the importer owns on `ApiEndpoint` — every successful sync treats the
# spec as the source of truth for these; `id`, `api`,
# `method`, `path`, `status`, `created_at`/`updated_at` are identity/lifecycle
# fields the upsert manages separately.
_ENDPOINT_DOC_FIELDS = (
    "operation_id",
    "summary",
    "description",
    "deprecated",
    "tags",
    "request",
    "responses",
    "external_docs",
    "security",
)


def sync_endpoints_from_spec(details: ApiDetails) -> None:
    """Parse `details.spec_content` and reconcile this API's `ApiEndpoint`
    rows to match it — a no-op for a non-`openapi`-typed API
    or empty `spec_content`. Never raises: a parse failure (or any other
    unexpected error) is logged and recorded via `endpoints_sync_failed`
    instead of propagating out of the caller's save/refresh path.
    """
    if details.type != ApiDetails.TYPE_OPENAPI or not details.spec_content:
        return

    api_label = str(details)
    try:
        operations = parse_operations(details.spec_content, api_label=api_label)
        spec = yaml.safe_load(details.spec_content)
        version = _version_of(spec)
        base_url, protocol = _resolve_servers(spec, version) if version else ("", "")
        with transaction.atomic():
            _upsert_operations(details.entity, operations)
    except Exception:
        logger.exception("Failed to sync endpoints for %s", api_label)
        details.endpoints_sync_failed = True
        details.save(update_fields=["endpoints_sync_failed"])
        return

    details.endpoints_synced_at = timezone.now()
    details.endpoints_sync_failed = False
    details.resolved_base_url = base_url
    details.resolved_protocol = protocol
    details.save(
        update_fields=[
            "endpoints_synced_at",
            "endpoints_sync_failed",
            "resolved_base_url",
            "resolved_protocol",
        ],
    )


def _upsert_operations(api: Any, operations: list[ParsedOperation]) -> None:
    """Create/update/revive an `ApiEndpoint` per parsed operation, then
    soft-remove every `active` endpoint whose `(method, path)` wasn't among
    them. Never deletes a row."""
    seen: set[tuple[str, str]] = set()
    for operation in operations:
        seen.add((operation.method, operation.path))
        _upsert_operation(api, operation)

    active = ApiEndpoint.objects.filter(api=api, status=ApiEndpoint.STATUS_ACTIVE)
    stale_ids = [
        endpoint.pk
        for endpoint in active
        if (endpoint.method, endpoint.path) not in seen
    ]
    # Saved one by one, not `QuerySet.update`: a bulk update sends no `post_save`, so search
    # indexing would never hear about the removal.
    for endpoint in ApiEndpoint.objects.filter(pk__in=stale_ids):
        endpoint.status = ApiEndpoint.STATUS_REMOVED
        endpoint.save(update_fields=["status", "updated_at"])


def _upsert_operation(api: Any, operation: ParsedOperation) -> None:
    doc_fields = {name: getattr(operation, name) for name in _ENDPOINT_DOC_FIELDS}
    endpoint = ApiEndpoint.objects.filter(
        api=api, method=operation.method, path=operation.path
    ).first()
    if endpoint is None:
        ApiEndpoint.objects.create(
            api=api, method=operation.method, path=operation.path, **doc_fields
        )
        return

    changed = endpoint.status == ApiEndpoint.STATUS_REMOVED
    for name, value in doc_fields.items():
        if getattr(endpoint, name) != value:
            setattr(endpoint, name, value)
            changed = True
    if not changed:
        return
    endpoint.status = ApiEndpoint.STATUS_ACTIVE
    endpoint.save()
