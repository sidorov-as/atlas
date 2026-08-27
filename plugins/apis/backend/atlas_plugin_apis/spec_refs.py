"""Shared `$ref` resolver used by both `asyncapi_import.py` and
`openapi_import.py` — resolves a
schema-shaped node's `$ref` values against the same document's
`components`/`definitions`, recursively, using `jsonpointer` for the actual
RFC 6901 pointer lookup. Not a general "resolve `$ref` anywhere
in any JSON" utility: the walk only recurses into positions a JSON
Schema/OpenAPI/AsyncAPI schema object actually uses to nest a subschema
 — `example`/`examples`/`default`/`enum`/`const` values are never
touched, even if they happen to contain a `$ref`-shaped key of their own.
"""

from typing import Any

import jsonpointer

# Positions a schema object nests a subschema in — the only places this walk
# recurses looking for a `$ref` to resolve.
_SCHEMA_LIST_KEYS = ("allOf", "oneOf", "anyOf")


def resolve_schema(
    node: Any,
    spec: dict,
    *,
    path: frozenset[str] = frozenset(),
    merge_siblings: bool = False,
) -> Any:
    """Recursively resolve `$ref` values found in `node` against `spec`.

    A `$ref` already being expanded along the current resolution `path` (a
    cycle) or one that doesn't resolve to anything in `spec` (dangling) is
    left as an unresolved `{"$ref": ...}` node instead of recursing further
    or raising. Sibling keys next to a `$ref` are
    merged onto the resolved result when `merge_siblings` is true (OpenAPI),
    or discarded entirely when it's false (AsyncAPI's default).
    """
    if isinstance(node, dict) and isinstance(node.get("$ref"), str):
        return _resolve_ref(node, spec, path=path, merge_siblings=merge_siblings)
    if isinstance(node, dict):
        return _resolve_dict(node, spec, path=path, merge_siblings=merge_siblings)
    if isinstance(node, list):
        return [
            resolve_schema(item, spec, path=path, merge_siblings=merge_siblings)
            for item in node
        ]
    return node


def _resolve_dict(
    node: dict, spec: dict, *, path: frozenset[str], merge_siblings: bool
) -> dict:
    resolved = dict(node)

    properties = node.get("properties")
    if isinstance(properties, dict):
        resolved["properties"] = {
            key: resolve_schema(value, spec, path=path, merge_siblings=merge_siblings)
            for key, value in properties.items()
        }

    if "items" in node:
        resolved["items"] = resolve_schema(
            node["items"], spec, path=path, merge_siblings=merge_siblings
        )

    additional_properties = node.get("additionalProperties")
    if isinstance(additional_properties, dict):
        resolved["additionalProperties"] = resolve_schema(
            additional_properties, spec, path=path, merge_siblings=merge_siblings
        )

    for key in _SCHEMA_LIST_KEYS:
        members = node.get(key)
        if isinstance(members, list):
            resolved[key] = [
                resolve_schema(member, spec, path=path, merge_siblings=merge_siblings)
                for member in members
            ]

    if "not" in node:
        resolved["not"] = resolve_schema(
            node["not"], spec, path=path, merge_siblings=merge_siblings
        )

    return resolved


def _resolve_ref(
    node: dict, spec: dict, *, path: frozenset[str], merge_siblings: bool
) -> Any:
    pointer = node["$ref"]
    siblings = {key: value for key, value in node.items() if key != "$ref"}
    normalized_pointer = pointer.removeprefix("#")

    if normalized_pointer in path:
        return _unresolved(node, pointer, merge_siblings=merge_siblings)

    try:
        target = jsonpointer.resolve_pointer(spec, normalized_pointer)
    except jsonpointer.JsonPointerException:
        return _unresolved(node, pointer, merge_siblings=merge_siblings)

    next_path = path | {normalized_pointer}
    resolved_target = resolve_schema(
        target, spec, path=next_path, merge_siblings=merge_siblings
    )

    if not siblings or not merge_siblings:
        return resolved_target

    resolved_siblings = {
        key: resolve_schema(value, spec, path=next_path, merge_siblings=merge_siblings)
        for key, value in siblings.items()
    }
    if isinstance(resolved_target, dict):
        return {**resolved_target, **resolved_siblings}
    return resolved_target


def _unresolved(node: dict, pointer: str, *, merge_siblings: bool) -> dict:
    """A cycle or dangling `$ref` couldn't be expanded — matches today's
    existing fallback shape, plus/minus the sibling
    keys per `merge_siblings`."""
    if merge_siblings:
        return dict(node)
    return {"$ref": pointer}
