"""AsyncAPI (2.x / 3.0) parsing into intermediate operation records
a hand-rolled walker over the
already-`yaml.safe_load`-parsed spec dict, mirroring `openapi_import.py`'s
own shape (no new spec object-model dependency).

`direction` is normalized to `ApiOperation`'s own `send`/`receive`
vocabulary here, never left as the raw, easy-to-invert 2.x `publish`/
`subscribe` keywords:
2.x `publish` → `receive`, 2.x `subscribe` → `send`; 3.0 `action` passes
through unchanged.

A message reference — a channel's `messages.<name>` entry, or (2.x) a bare
`publish`/`subscribe`/`oneOf` message field — that is itself an unresolved
`{"$ref": ...}` rather than the real Message Object is dereferenced through
as many hops as the document actually chains (typically into
`components.messages`), with its own cycle guard; a message's `payload` is then resolved against
`components.schemas` via the shared `spec_refs.resolve_schema`,
recursively, with sibling keys next to a `$ref` discarded (`merge_siblings`
defaults to `False`, matching AsyncAPI's own Reference Object semantics).
"""

import logging
from dataclasses import dataclass, field
from typing import Any

import jsonpointer
import yaml
from django.db import transaction
from django.utils import timezone

from atlas_plugin_apis import spec_refs
from atlas_plugin_apis.models import ApiDetails, ApiOperation

logger = logging.getLogger("atlas_plugin_apis")

VERSION_2X = "asyncapi2"
VERSION_3X = "asyncapi3"

_2X_DIRECTION_MAP = {
    "publish": ApiOperation.DIRECTION_RECEIVE,
    "subscribe": ApiOperation.DIRECTION_SEND,
}


class SpecParseError(Exception):
    """`spec_content` has no recognizable version key or no usable
    `channels`/`operations`."""


@dataclass
class ParsedOperation:
    """One channel operation, normalized to the shape the upsert writes
    into `ApiOperation`."""

    channel_address: str
    channel_protocol: str
    direction: str
    operation_key: str
    operation_id: str = ""
    summary: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    message: list[dict[str, Any]] = field(default_factory=list)
    external_docs: dict = field(default_factory=dict)


def detect_spec_version(spec_content: str) -> str | None:
    """Load `spec_content` and report which of `asyncapi: "2.x"` /
    `asyncapi: "3.x"` / neither it declares itself as."""
    try:
        spec = yaml.safe_load(spec_content)
    except yaml.YAMLError:
        return None
    return _version_of(spec)


def _version_of(spec: Any) -> str | None:
    if not isinstance(spec, dict):
        return None
    version = spec.get("asyncapi")
    if not isinstance(version, str):
        return None
    if version.startswith("2."):
        return VERSION_2X
    if version.startswith("3."):
        return VERSION_3X
    return None


def parse_operations(
    spec_content: str, *, api_label: str = ""
) -> list[ParsedOperation]:
    """Parse `spec_content` into intermediate operation records.

       Raises `SpecParseError` for a spec-level failure (invalid YAML/JSON, no
       recognizable version key, no usable `channels`/`operations`) — callers
    treat that as a whole-sync failure. A single channel/operation that
       doesn't map cleanly is logged and skipped instead of aborting the rest of
       the parse. `api_label`, when given, is included in that
       per-operation log line.
    """
    try:
        spec = yaml.safe_load(spec_content)
    except yaml.YAMLError as exc:
        raise SpecParseError("spec_content is not valid YAML/JSON") from exc

    version = _version_of(spec)
    if version is None:
        raise SpecParseError("spec_content has no recognizable asyncapi version key")

    if version == VERSION_2X:
        return _parse_channels_2x(spec, api_label=api_label)
    return _parse_operations_3x(spec, api_label=api_label)


# --- 2.x: channels -> publish/subscribe -------------------------------------


def _parse_channels_2x(spec: dict, *, api_label: str) -> list[ParsedOperation]:
    channels = spec.get("channels")
    if not isinstance(channels, dict):
        raise SpecParseError("spec_content has no usable channels")

    protocol = _resolve_protocol_2x(spec)
    operations: list[ParsedOperation] = []
    for channel_address, channel in channels.items():
        if not isinstance(channel, dict):
            continue
        for keyword in ("publish", "subscribe"):
            operation = channel.get(keyword)
            if not isinstance(operation, dict):
                continue
            try:
                operations.append(
                    _parse_operation_2x(
                        channel_address, keyword, operation, protocol, spec
                    )
                )
            except Exception:
                logger.warning(
                    "Skipping malformed AsyncAPI operation %s on channel %s%s",
                    keyword,
                    channel_address,
                    f" on {api_label}" if api_label else "",
                    exc_info=True,
                )
    return operations


def _parse_operation_2x(
    channel_address: str, keyword: str, operation: dict, protocol: str, spec: dict
) -> ParsedOperation:
    direction = _2X_DIRECTION_MAP[keyword]
    return ParsedOperation(
        channel_address=channel_address,
        channel_protocol=protocol,
        direction=direction,
        operation_key=f"{channel_address}-{direction}",
        operation_id=operation.get("operationId") or "",
        summary=operation.get("summary") or "",
        description=operation.get("description") or "",
        tags=_extract_tags(operation.get("tags")),
        message=_extract_messages_2x(operation.get("message"), spec),
        external_docs=_extract_external_docs(operation.get("externalDocs")),
    )


def _resolve_protocol_2x(spec: dict) -> str:
    """A 2.x document has no per-channel server scoping — resolvable only when the document declares exactly one top-level
    server."""
    servers = spec.get("servers")
    if not isinstance(servers, dict) or len(servers) != 1:
        return ""
    server = next(iter(servers.values()))
    return server.get("protocol") or "" if isinstance(server, dict) else ""


def _extract_messages_2x(message_field: Any, spec: dict) -> list[dict[str, Any]]:
    if not isinstance(message_field, dict):
        return []
    one_of = message_field.get("oneOf")
    if isinstance(one_of, list):
        return [
            _map_message_field_2x(msg, spec) for msg in one_of if isinstance(msg, dict)
        ]
    return [_map_message_field_2x(message_field, spec)]


def _map_message_field_2x(node: dict, spec: dict) -> dict[str, Any]:
    """A `publish`/`subscribe`/`oneOf` message field, possibly itself a bare
    `{"$ref": ...}` rather than an inline Message Object — dereferenced the same way as the 3.0 path."""
    message = _dereference_message(node, spec)
    if message is not None:
        return _map_message(message, spec)
    return _message_stub(_ref_name(node.get("$ref")))


# --- 3.0: operations map -> channel reference --------------------------------


def _parse_operations_3x(spec: dict, *, api_label: str) -> list[ParsedOperation]:
    operations_map = spec.get("operations")
    if not isinstance(operations_map, dict):
        raise SpecParseError("spec_content has no usable operations")

    channels_map = spec.get("channels")
    channels_map = channels_map if isinstance(channels_map, dict) else {}
    servers_map = spec.get("servers")
    servers_map = servers_map if isinstance(servers_map, dict) else {}

    operations: list[ParsedOperation] = []
    for operation_key, operation in operations_map.items():
        if not isinstance(operation, dict):
            continue
        try:
            operations.append(
                _parse_operation_3x(
                    operation_key, operation, channels_map, servers_map, spec
                )
            )
        except Exception:
            logger.warning(
                "Skipping malformed AsyncAPI operation %s%s",
                operation_key,
                f" on {api_label}" if api_label else "",
                exc_info=True,
            )
    return operations


def _parse_operation_3x(
    operation_key: str,
    operation: dict,
    channels_map: dict,
    servers_map: dict,
    spec: dict,
) -> ParsedOperation:
    direction = operation.get("action")
    if direction not in (ApiOperation.DIRECTION_SEND, ApiOperation.DIRECTION_RECEIVE):
        raise ValueError(f"unrecognized action {direction!r}")

    channel_ref = operation.get("channel")
    ref = channel_ref.get("$ref") if isinstance(channel_ref, dict) else None
    channel = channels_map.get(_ref_name(ref)) if ref else None
    if not isinstance(channel, dict):
        raise TypeError(f"unresolved channel reference {ref!r}")

    return ParsedOperation(
        channel_address=channel.get("address") or "",
        channel_protocol=_resolve_protocol_3x(channel, servers_map),
        direction=direction,
        operation_key=operation_key,
        operation_id=operation.get("title") or "",
        summary=operation.get("summary") or "",
        description=operation.get("description") or "",
        tags=_extract_tags(operation.get("tags")),
        message=_extract_messages_3x(operation, channel, spec),
        external_docs=_extract_external_docs(operation.get("externalDocs")),
    )


def _resolve_protocol_3x(channel: dict, servers_map: dict) -> str:
    """Resolvable only when the channel's own `servers` list references
    exactly one entry of the document's top-level `servers` map."""
    server_refs = channel.get("servers")
    if not isinstance(server_refs, list) or len(server_refs) != 1:
        return ""
    server_ref = server_refs[0]
    ref = server_ref.get("$ref") if isinstance(server_ref, dict) else None
    server = servers_map.get(_ref_name(ref)) if ref else None
    return server.get("protocol") or "" if isinstance(server, dict) else ""


def _extract_messages_3x(
    operation: dict, channel: dict, spec: dict
) -> list[dict[str, Any]]:
    """Resolve the operation's `messages` (a list of `$ref`s into the
    channel's own `messages` map) into mapped message entries, dereferencing
    each channel-map entry through as many further `$ref` hops as the
    document chains before falling back to a
    name-only entry (only for a dangling pointer or a real cycle). An
    operation with no `messages` narrowing covers every message the channel
    defines — including one that's itself still a `$ref`, not only ones with
    an inline `payload`."""
    channel_messages = channel.get("messages")
    channel_messages = channel_messages if isinstance(channel_messages, dict) else {}

    message_refs = operation.get("messages")
    if isinstance(message_refs, list) and message_refs:
        mapped = []
        for message_ref in message_refs:
            ref = message_ref.get("$ref") if isinstance(message_ref, dict) else None
            if not ref:
                continue
            name = _ref_name(ref)
            mapped.append(
                _map_channel_message_entry(name, channel_messages.get(name), spec)
            )
        return mapped

    return [
        _map_channel_message_entry(name, node, spec)
        for name, node in channel_messages.items()
    ]


def _map_channel_message_entry(name: str, node: Any, spec: dict) -> dict[str, Any]:
    message = _dereference_message(node, spec)
    if message is not None:
        return _map_message(message, spec)
    return _message_stub(name)


def _dereference_message(node: Any, spec: dict) -> dict[str, Any] | None:
    """Follow a chain of `{"$ref": ...}` hops (typically into
    `components.messages`) until a real Message Object is reached — a dict
    that is *not itself* a `$ref` (every Message
    Object field, including `payload`, is optional, so "has a payload" is
    not the right stop condition). Returns `None` for a dangling pointer or
    a reference cycle (own `path` cycle guard, separate from
    `spec_refs.py`'s)."""
    path: frozenset[str] = frozenset()
    while isinstance(node, dict) and isinstance(node.get("$ref"), str):
        pointer = node["$ref"]
        normalized_pointer = pointer.removeprefix("#")
        if normalized_pointer in path:
            return None
        try:
            node = jsonpointer.resolve_pointer(spec, normalized_pointer)
        except jsonpointer.JsonPointerException:
            return None
        path = path | {normalized_pointer}
    return node if isinstance(node, dict) else None


def _message_stub(name: str) -> dict[str, Any]:
    return {
        "name": name,
        "title": "",
        "summary": "",
        "content_type": "",
        "schema": None,
        "example": None,
    }


def _ref_name(ref: Any) -> str:
    return ref.rsplit("/", 1)[-1] if isinstance(ref, str) and ref else ""


# --- shared: message / tag mapping -------------------------------------------


def _map_message(message: dict, spec: dict) -> dict[str, Any]:
    """`payload` -> schema, resolved against `components.schemas`
    (`spec_refs.resolve_schema`, `merge_siblings=False` default — AsyncAPI's
    own Reference Object semantics discard sibling keys); the first `examples[]` entry's `payload` -> example (unchanged).
    `headers` -> a `headers` schema, resolved the same way
    omitted
    entirely, not stored as an empty/`null` placeholder, when the message
    declares no `headers`."""
    payload = message.get("payload")
    schema = (
        spec_refs.resolve_schema(payload, spec) if isinstance(payload, dict) else None
    )

    headers = message.get("headers")
    resolved_headers = (
        spec_refs.resolve_schema(headers, spec) if isinstance(headers, dict) else None
    )

    example = None
    examples = message.get("examples")
    if isinstance(examples, list) and examples:
        first = examples[0]
        if isinstance(first, dict):
            example = first.get("payload")

    mapped = {
        "name": message.get("name") or "",
        "title": message.get("title") or "",
        "summary": message.get("summary") or "",
        "content_type": message.get("contentType") or "",
        "schema": schema,
        "example": example,
    }
    if resolved_headers is not None:
        mapped["headers"] = resolved_headers
    return mapped


def _extract_tags(tags: Any) -> list[str]:
    if not isinstance(tags, list):
        return []
    return [
        tag["name"]
        for tag in tags
        if isinstance(tag, dict) and isinstance(tag.get("name"), str)
    ]


def _extract_external_docs(external_docs: Any) -> dict[str, str]:
    """An Operation Object's `externalDocs` (`{description?, url}`, identical
    shape in both 2.x and 3.0). Only stored when a
    non-empty `url` is present; missing or url-less `externalDocs` yields
    `{}`, same as a missing field."""
    if not isinstance(external_docs, dict):
        return {}
    url = external_docs.get("url")
    if not url:
        return {}
    return {"description": external_docs.get("description") or "", "url": url}


# --- Upsert / lifecycle sync -------------------------------------------------

# Fields the importer owns on `ApiOperation` — every successful sync treats the
# spec as the source of truth for these (mirroring `openapi_import.py`); `id`, `api`, `operation_key`, `status`, `created_at`/`updated_at`
# are identity/lifecycle fields the upsert manages separately.
_OPERATION_DOC_FIELDS = (
    "channel_address",
    "channel_protocol",
    "direction",
    "operation_id",
    "summary",
    "description",
    "tags",
    "message",
    "external_docs",
)


def sync_operations_from_spec(details: ApiDetails) -> None:
    """Parse `details.spec_content` and reconcile this API's `ApiOperation`
    rows to match it — a no-op for a non-`asyncapi`-typed API
    or empty `spec_content`. Never raises: a parse failure (or any other
    unexpected error) is logged and recorded via `operations_sync_failed`
    instead of propagating out of the caller's save/refresh path.
    """
    if details.type != ApiDetails.TYPE_ASYNCAPI or not details.spec_content:
        return

    api_label = str(details)
    try:
        operations = parse_operations(details.spec_content, api_label=api_label)
        with transaction.atomic():
            _upsert_operations(details.entity, operations)
    except Exception:
        logger.exception("Failed to sync operations for %s", api_label)
        details.operations_sync_failed = True
        details.save(update_fields=["operations_sync_failed"])
        return

    details.operations_synced_at = timezone.now()
    details.operations_sync_failed = False
    details.save(update_fields=["operations_synced_at", "operations_sync_failed"])


def _upsert_operations(api: Any, operations: list[ParsedOperation]) -> None:
    """Create/update/revive an `ApiOperation` per parsed operation, then
    soft-remove every `active` operation whose `operation_key` wasn't among
    them. Never deletes a row."""
    seen: set[str] = set()
    for operation in operations:
        seen.add(operation.operation_key)
        _upsert_operation(api, operation)

    active = ApiOperation.objects.filter(api=api, status=ApiOperation.STATUS_ACTIVE)
    stale_ids = [op.pk for op in active if op.operation_key not in seen]
    # Saved one by one, not `QuerySet.update`: a bulk update sends no `post_save`, so search
    # indexing would never hear about the removal.
    for operation in ApiOperation.objects.filter(pk__in=stale_ids):
        operation.status = ApiOperation.STATUS_REMOVED
        operation.save(update_fields=["status", "updated_at"])


def _upsert_operation(api: Any, operation: ParsedOperation) -> None:
    doc_fields = {name: getattr(operation, name) for name in _OPERATION_DOC_FIELDS}
    existing = ApiOperation.objects.filter(
        api=api, operation_key=operation.operation_key
    ).first()
    if existing is None:
        ApiOperation.objects.create(
            api=api, operation_key=operation.operation_key, **doc_fields
        )
        return

    changed = existing.status == ApiOperation.STATUS_REMOVED
    for name, value in doc_fields.items():
        if getattr(existing, name) != value:
            setattr(existing, name, value)
            changed = True
    if not changed:
        return
    existing.status = ApiOperation.STATUS_ACTIVE
    existing.save()
