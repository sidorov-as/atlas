"""Shared `kind:name` ref resolver (`core-plugin-contract-surface` spec: "Core
publishes its plugin-facing surface as contract types").

Canonical home for the ref-string parser/resolver — previously
`server.apps.catalog.refs`. `parse_ref` needs no Django model at all;
`resolve_ref` needs only a real `CatalogEntity` query, available through
`get_catalog_entity_model()` (catalog.py) without importing the concrete
model — so, like `kinds.py`, this moves here outright rather than staying in
`server` behind a wrapper. `server.apps.catalog.refs` re-exports it for
Core's own internal call sites.

Ref strings are a computed representation, not the storage format — spec
reference fields are real FK/M2M columns, and this module is the one place
ref strings get parsed into rows or built from them. Refs are parsed as
`[kind:][namespace/]name` from day one per ADR 0004, even though namespace is
always "default" and never settable in v1.
"""

import re
from typing import Any

from .catalog import KIND_CHOICES, get_catalog_entity_model

REF_PATTERN = re.compile(
    r"^(?:(?P<kind>[A-Za-z][\w-]*):)?(?:(?P<namespace>[^/:]+)/)?(?P<name>[^/]+)$",
)

DEFAULT_NAMESPACE = "default"

_VALID_KINDS = frozenset(kind for kind, _label in KIND_CHOICES)


class RefError(ValueError):
    """A ref string couldn't be parsed or resolved to an entity."""


def parse_ref(ref: str, *, default_kind: str | None = None) -> tuple[str, str, str]:
    """Parse `[kind:][namespace/]name` into `(kind, namespace, name)`."""
    match = REF_PATTERN.match(ref.strip()) if ref else None
    if not match:
        raise RefError(f"Invalid entity ref: {ref!r}")

    kind = match.group("kind") or default_kind
    if not kind:
        raise RefError(f"Entity ref {ref!r} has no kind and none was inferred")

    namespace = match.group("namespace") or DEFAULT_NAMESPACE
    name = match.group("name")
    return kind.lower(), namespace, name


def resolve_ref(ref: str, *, expected_kind: str | None = None) -> Any:
    """Resolve a ref string to its `CatalogEntity` row, or raise `RefError`."""
    kind, namespace, name = parse_ref(ref, default_kind=expected_kind)
    if expected_kind and kind != expected_kind:
        raise RefError(
            f"Expected a {expected_kind!r} ref, got kind {kind!r} in {ref!r}"
        )

    if kind not in _VALID_KINDS:
        raise RefError(f"Unknown entity kind: {kind!r}")

    model = get_catalog_entity_model()
    try:
        return model.objects.get(
            kind=kind, namespace__iexact=namespace, name__iexact=name
        )
    except model.DoesNotExist:
        raise RefError(f"No {kind} entity found for ref {ref!r}") from None
