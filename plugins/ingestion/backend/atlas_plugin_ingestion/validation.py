"""Per-manifest-document schema validation.

Reuses the same pydantic envelope schemas the CRUD API validates request
bodies against (`atlas_plugin_apis.contracts` / `atlas_plugin_standard_catalog.
contracts`) — a `catalog-info.yaml` document and a `POST /api/systems/`
body share the same `apiVersion`/`kind`/`metadata`/`spec` shape, so one set
of schemas is the single source of truth for both. Group is deliberately
absent: a manifest may only declare System, Component, Resource, API, or
User/Actor (Actor becomes ingestible; Team does not).
"""

from typing import Any

from atlas_plugin_apis.contracts import ApiIn
from atlas_plugin_standard_catalog.contracts import (
    ActorIn,
    ComponentIn,
    ResourceIn,
    SystemIn,
)
from pydantic import ValidationError

ManifestDocument = ActorIn | ApiIn | ComponentIn | ResourceIn | SystemIn

_KIND_SCHEMAS: dict[str, type[ManifestDocument]] = {
    "System": SystemIn,
    "Component": ComponentIn,
    "Resource": ResourceIn,
    "API": ApiIn,
    "User": ActorIn,
}


class ManifestError(Exception):
    """A manifest document failed schema validation."""


def validate_manifest_document(raw: Any) -> ManifestDocument:
    kind = raw.get("kind") if isinstance(raw, dict) else None
    schema = _KIND_SCHEMAS.get(kind)
    if schema is None:
        raise ManifestError(f"Unsupported or missing kind: {kind!r}")

    try:
        document = schema.model_validate(raw)
    except ValidationError as exc:
        raise ManifestError(str(exc)) from exc

    return document
