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
from pydantic import ConfigDict, Field


class StrictMetadataIn(MetadataIn):
    """`MetadataIn` that rejects unknown keys instead of ignoring them, so a
    misspelled `metadata` field fails the write rather than vanishing."""

    model_config = ConfigDict(extra="forbid")


class StrictMetadataPatch(MetadataPatch):
    model_config = ConfigDict(extra="forbid")


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
    set — `views.WRITABLE_KINDS`); `spec` is validated against that kind's
    own `EntityKindHandler.spec_schema` at request-handling time, not here —
    there is no single fixed shape across kinds for this field to declare
    (schemas.py's own module docstring), matching `CatalogEntityOut.spec`'s
    read-side `dict[str, Any]`. `owner` lives inside `spec` for every
    currently writable kind (e.g. `ComponentSpecIn.owner`), read back out by
    `atlas_plugin_api.spec_owner_ref` after validation, the same way the
    existing REST create controllers do.
    """

    kind: str
    metadata: StrictMetadataIn
    spec: dict[str, Any] = Field(default_factory=dict)


class UpdateEntityIn(CamelModel):
    """Body for the `update_entity` MCP tool — a true partial patch, like the
    existing REST PATCH endpoints: an omitted field is left untouched.
    `spec`, when present, is validated against the target entity's *current*
    kind's `EntityKindHandler.patch_schema` (views.py resolves the kind from
    the entity itself, not from client input, so a client can't smuggle a
    spec shaped for a different kind past the wrong handler).
    """

    metadata: StrictMetadataPatch | None = None
    spec: dict[str, Any] | None = None


# --- Architecture Relationship tools --------------------------------------
#
# MCP-owned shapes, not core's SPA-facing `ArchitectureRelationshipIn/Out`
# (design.md Decision 2): an unrelated SPA schema change must not silently
# reshape a tool's input or output.

RelationshipInteractionKind = Literal[
    "synchronous", "asynchronous", "data-access", "manual"
]


class RelationshipPath(CamelModel):
    id: int


class ListRelationshipsQuery(CamelModel):
    entity: str = Field(
        description="Entity ref (`kind:name`) whose incoming and outgoing "
        "relationships to list."
    )


class CreateRelationshipIn(CamelModel):
    model_config = ConfigDict(extra="forbid")

    source: str = Field(
        description="Source entity ref; a System, Component, Resource, or API."
    )
    target: str = Field(description="Target entity ref; any catalog entity.")
    label: str = Field(min_length=1, max_length=255)
    technology: str = Field(default="", max_length=255)
    interaction_kind: RelationshipInteractionKind = "manual"
    tags: list[str] = Field(default_factory=list)


class UpdateRelationshipIn(CamelModel):
    """Partial update: an omitted field is left untouched. The source cannot
    change; delete and recreate the relationship instead."""

    model_config = ConfigDict(extra="forbid")

    target: str | None = None
    label: str | None = Field(default=None, min_length=1, max_length=255)
    technology: str | None = Field(default=None, max_length=255)
    interaction_kind: RelationshipInteractionKind | None = None
    tags: list[str] | None = None


class RelationshipOut(CamelModel):
    id: int
    source: str
    source_kind: str
    target: str
    target_kind: str
    label: str
    technology: str
    interaction_kind: str
    tags: list[str]
    origin: Literal["manual", "yaml"]


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


class DescribeKindsQuery(CamelModel):
    kind: str | None = None


class KindDescriptionOut(CamelModel):
    """One MCP-writable kind: the JSON Schema (by alias, so camelCase) of
    the `spec` that `create_entity` and `update_entity` accept for it."""

    kind: str
    create_spec: dict[str, Any]
    patch_spec: dict[str, Any]


# --- Dry-run ----------------------------------------------------------------


class DryRunQuery(CamelModel):
    dry_run: bool = Field(
        default=False,
        description="Preview the write: run it for real, report the result "
        "and the field-level changes, then roll everything back.",
    )


class FieldChangeOut(CamelModel):
    field: str = Field(description="Dotted path, e.g. `spec.lifecycle`.")
    before: Any = Field(description="Current value; null for a create.")
    after: Any = Field(description="Proposed value; null for a delete.")


class DryRunOut(CamelModel):
    """The response of a write called with `dryRun`: nothing was saved."""

    dry_run: Literal[True] = True
    result: dict[str, Any] | None = Field(
        description="The state after the write (what the normal response "
        "would carry, with `id` null for a create); null for a delete."
    )
    changes: list[FieldChangeOut]
    warnings: list[str] = Field(
        description="Effects a real write would have that a dry-run skips."
    )


class ValidateFlowIn(CamelModel):
    """Body for `validate_flow`: the `create_flow` fields, but `steps` stay
    plain objects so a malformed step is reported as a violation instead of
    rejecting the whole request."""

    flow_id: int | None = Field(
        default=None,
        description="Id of the existing flow this body would replace, if "
        "validating an update.",
    )
    system: str
    name: str
    description: str = ""
    documentation: str = ""
    steps: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Steps in the same shape `create_flow` takes.",
    )
    autolayout_enabled: bool = True
    layout_direction: str = "LAYOUT_LEFT_RIGHT"
    layout_engine: str = "dagre"


class ValidateFlowOut(CamelModel):
    valid: bool
    violations: list[str]
