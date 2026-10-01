"""Pydantic request/response envelope models for the MCP API.

Deliberately its own, small vocabulary, not the SPA-facing API's per-kind
schemas (`atlas_plugin_standard_catalog.api.schemas.SystemOut`, and so on) —
`mcp-plugin` spec's "SHALL NOT re-expose the SPA-facing API's endpoints
under this document" and design.md Decision 2 ("the existing document is
UI-shaped ... would produce a chatty, badly-scoped tool list"). A
`search_catalog` result is intentionally kind-agnostic (`CatalogEntitySummaryOut`
carries the same handful of fields regardless of `kind`); `get_entity`
returns the target's full metadata plus its kind handler's own `spec`,
serialized as a plain `dict` rather than a fixed per-kind model, since the
concrete spec shape genuinely varies by `kind` and this API has no
"one schema per kind" endpoint split for a tool-calling client to route on.
"""

from typing import Any, Literal
from uuid import UUID

from atlas_plugin_api import CamelModel, MetadataIn, MetadataOut, MetadataPatch
from pydantic import Field


class SearchCatalogQuery(CamelModel):
    q: str | None = None
    kind: str | None = None
    owner: str | None = None
    tags: list[str] = Field(default_factory=list)
    status: Literal["active", "all"] = "active"
    page: int = 1
    page_size: int = Field(default=20, le=100)
    sort: Literal["name", "-name"] = "name"


class CatalogEntitySummaryOut(CamelModel):
    id: UUID
    ref: str
    kind: str
    name: str
    title: str
    description: str
    status: str
    owner: str | None


class CatalogEntityOut(CamelModel):
    id: UUID
    ref: str
    kind: str
    metadata: MetadataOut
    status: str
    spec: dict[str, Any] | None
    unavailable: bool


class CreateEntityIn(CamelModel):
    """Body for the `create_entity` MCP tool.

    `kind` picks the target Entity Kind (restricted to `atlas.mcp`'s writable
    set — `views._WRITABLE_KINDS`); `spec` is validated against that kind's
    own `EntityKindHandler.spec_schema` at request-handling time, not here —
    there is no single fixed shape across kinds for this field to declare
    (schemas.py's own module docstring), matching `CatalogEntityOut.spec`'s
    read-side `dict[str, Any]`. `owner` lives inside `spec` for every
    currently writable kind (e.g. `ComponentSpecIn.owner`), read back out by
    `atlas_plugin_api.spec_owner_ref` after validation, the same way the
    existing REST create controllers do.
    """

    kind: str
    metadata: MetadataIn
    spec: dict[str, Any] = Field(default_factory=dict)


class UpdateEntityIn(CamelModel):
    """Body for the `update_entity` MCP tool — a true partial patch, like the
    existing REST PATCH endpoints: an omitted field is left untouched.
    `spec`, when present, is validated against the target entity's *current*
    kind's `EntityKindHandler.patch_schema` (views.py resolves the kind from
    the entity itself, not from client input, so a client can't smuggle a
    spec shaped for a different kind past the wrong handler).
    """

    metadata: MetadataPatch | None = None
    spec: dict[str, Any] | None = None


class FlowPath(CamelModel):
    id: int


class FlowSummaryOut(CamelModel):
    id: int
    system: str
    name: str
    description: str


class FlowOut(CamelModel):
    id: int
    system: str
    name: str
    description: str
    documentation: str
    steps: list[dict]
    autolayout_enabled: bool
    layout_direction: str
    layout_engine: str


class FlowListQuery(CamelModel):
    system: str | None = None
    team: str | None = None
    q: str | None = None
    page: int = 1
    page_size: int = Field(default=20, le=100)
    sort: Literal["name", "-name"] = "name"


# --- API Endpoint/Operation tools (`atlas.apis`) --------------------------
#
# MCP-owned read shapes, not `atlas_plugin_apis.api.schemas`'s SPA-facing
# ones (design.md Decision 2): an unrelated SPA schema change must not
# silently reshape a tool's output. `request`/`responses`/`security`/
# `messages` pass `ApiEndpoint`/`ApiOperation`'s stored JSON through as-is
# rather than re-declaring its nested schema vocabulary a second time.


class ApiEndpointSearchQuery(CamelModel):
    q: str = ""
    api_id: UUID | None = None
    page: int = 1
    page_size: int = Field(default=20, le=100)


class ApiOperationSearchQuery(ApiEndpointSearchQuery):
    pass


class EndpointPath(CamelModel):
    id: UUID


class OperationPath(CamelModel):
    id: UUID


class EndpointSummaryOut(CamelModel):
    id: UUID
    api: str
    api_id: UUID
    method: str
    path: str
    summary: str
    deprecated: bool
    status: str


class EndpointOut(EndpointSummaryOut):
    operation_id: str
    description: str
    tags: list[str]
    request: dict[str, Any]
    responses: list[dict[str, Any]]
    security: list[dict[str, Any]]
    external_docs: dict[str, Any] | None


class OperationSummaryOut(CamelModel):
    id: UUID
    api: str
    api_id: UUID
    channel_address: str
    channel_protocol: str
    direction: str
    summary: str
    deprecated: bool
    status: str


class OperationOut(OperationSummaryOut):
    operation_key: str
    operation_id: str
    description: str
    tags: list[str]
    messages: list[dict[str, Any]]
    external_docs: dict[str, Any] | None


class ConsumerServiceOut(CamelModel):
    id: UUID
    ref: str
    name: str
    title: str
    team: str | None


class OperationConsumerOut(CamelModel):
    service: ConsumerServiceOut
    role: Literal["publisher", "subscriber"]


class EndpointConsumersOut(CamelModel):
    endpoint: EndpointSummaryOut
    services: list[ConsumerServiceOut]


class OperationConsumersOut(CamelModel):
    operation: OperationSummaryOut
    participants: list[OperationConsumerOut]
