"""The `describe_kinds` MCP tool (`mcp-kind-introspection` spec).

An entity's `spec` is an untyped object in this API's OpenAPI document, so
a client has no other way to learn a kind's fields, enums, and limits. This
derives them from the registered handlers' own `spec_schema` and
`patch_schema` — the schemas the write operations validate against — so the
answer cannot drift from what a write accepts, and a kind from an optional
plugin appears only when that plugin registered it.

`relationships` is dropped from both schemas: the shared `*SpecIn` declares
it for ingestion, but a write through MCP rejects it (`strict_keys`) and
points at the relationship tools.
"""

from typing import Any

from atlas_plugin_api import (
    FORBIDDEN_RESPONSE,
    EntityKindHandler,
    PATBearerAuth,
    registry,
    require_scope,
)
from atlas_plugin_api.controllers import AtlasController
from dmr import Query, modify
from pydantic import BaseModel

from .schemas import DescribeKindsQuery, KindDescriptionOut
from .strict_keys import RELATIONSHIPS_KEY
from .views import WRITABLE_KINDS, _unwritable_kind

_SCOPE_CATALOG_READ = "catalog:read"


def _writable_schema(schema: type[BaseModel]) -> dict[str, Any]:
    json_schema = schema.model_json_schema(by_alias=True)
    json_schema.get("properties", {}).pop(RELATIONSHIPS_KEY, None)
    required = json_schema.get("required")
    if required is not None:
        json_schema["required"] = [
            name for name in required if name != RELATIONSHIPS_KEY
        ]
    return json_schema


def _describe(handler: EntityKindHandler) -> KindDescriptionOut:
    return KindDescriptionOut(
        kind=handler.kind_id,
        create_spec=_writable_schema(handler.spec_schema),
        patch_spec=_writable_schema(handler.patch_schema),
    )


class DescribeKindsController(AtlasController):
    auth = (PATBearerAuth(),)

    @modify(
        operation_id="describe_kinds",
        summary="Describe the writable entity kinds",
        description=(
            "For each kind `create_entity` and `update_entity` can write "
            "(and that is installed here), return the JSON Schema of its "
            "`spec` for create and for update: field names, types, enum "
            "values, required fields, and limits. Pass `kind` to describe "
            "just one. Relationships are not part of `spec`: use the "
            "relationship tools. Requires the `catalog:read` PAT scope."
        ),
        extra_responses=[FORBIDDEN_RESPONSE],
    )
    def get(self, parsed_query: Query[DescribeKindsQuery]) -> list[KindDescriptionOut]:
        require_scope(self, _SCOPE_CATALOG_READ)
        if parsed_query.kind is not None:
            if parsed_query.kind not in WRITABLE_KINDS:
                raise _unwritable_kind(parsed_query.kind)
            handler = registry.resolve(parsed_query.kind)
            if handler is None:
                raise _unwritable_kind(parsed_query.kind)
            return [_describe(handler)]
        return [
            _describe(handler)
            for kind_id in registry.registered_ids()
            if kind_id in WRITABLE_KINDS
            and (handler := registry.resolve(kind_id)) is not None
        ]
