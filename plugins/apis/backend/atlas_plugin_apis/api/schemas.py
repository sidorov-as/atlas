"""Pydantic request/response envelope models for the API kind — split out of
`server.apps.catalog.api.schemas`.
"""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from atlas_plugin_api import (
    ArchitectureRelationshipDeclarationIn,
    CamelModel,
    EntityPermissionsOut,
    MetadataIn,
    MetadataOut,
    MetadataPatch,
    optional_ref_validator,
    ref_validator,
)
from pydantic import BaseModel, Field, field_validator

# --- API ----------------------------------------------------------------

ApiType = Literal["openapi", "grpc", "asyncapi", "graphql"]
ApiSpecSource = Literal["none", "inline", "url"]

# Generous DoS-prevention bound for user-submitted inline spec content
# The `url` source bypasses this
# Pydantic-layer limit entirely by writing `ApiDetails.spec_content` directly
# (`spec_fetch.resolve_api_spec_url`), so it's bounded separately and more
# generously by `spec_fetch.MAX_SPEC_RESPONSE_BYTES` (20 MiB) — `inline`
# content instead arrives as part of the Django request body, which Django's
# (unconfigured, default) `DATA_UPLOAD_MAX_MEMORY_SIZE` already hard-caps at
# 2.5 MiB ahead of any Pydantic validation; a `max_length` at or above that
# would never actually fire (Django would reject the whole request first,
# as an unattributed 422, before this validator runs), so this is kept
# safely below it instead.
_SPEC_CONTENT_MAX_LENGTH = 2 * 1024 * 1024


class ApiSpecIn(CamelModel):
    type: ApiType
    owner: str
    system: str
    spec_source: ApiSpecSource = "none"
    spec_url: str = ""
    spec_content: str = Field(default="", max_length=_SPEC_CONTENT_MAX_LENGTH)
    relationships: list[ArchitectureRelationshipDeclarationIn] = Field(
        default_factory=list
    )

    _validate_owner = field_validator("owner")(ref_validator("group"))
    _validate_system = field_validator("system")(ref_validator("system"))


class ApiSpecPatch(CamelModel):
    type: ApiType | None = None
    owner: str | None = None
    system: str | None = None
    spec_source: ApiSpecSource | None = None
    spec_url: str | None = None
    spec_content: str | None = Field(default=None, max_length=_SPEC_CONTENT_MAX_LENGTH)

    _validate_owner = field_validator("owner")(optional_ref_validator("group"))
    _validate_system = field_validator("system")(optional_ref_validator("system"))


class ApiSpecOut(CamelModel):
    type: ApiType
    owner: str
    owner_id: UUID
    system: str
    system_id: UUID | None
    spec_source: ApiSpecSource
    spec_url: str
    spec_content: str
    spec_resolved_at: datetime | None = None
    spec_resolve_failed: bool
    endpoints_synced_at: datetime | None = None
    endpoints_sync_failed: bool
    operations_synced_at: datetime | None = None
    operations_sync_failed: bool
    resolved_base_url: str = ""
    resolved_protocol: str = ""


class ApiIn(CamelModel):
    api_version: str = "atlas/v1alpha1"
    kind: Literal["API"] = "API"
    metadata: MetadataIn
    spec: ApiSpecIn


class ApiPatch(CamelModel):
    metadata: MetadataPatch | None = None
    spec: ApiSpecPatch | None = None


class ApiOut(CamelModel):
    id: UUID
    api_version: str
    kind: Literal["API"] = "API"
    metadata: MetadataOut
    spec: ApiSpecOut
    status: Literal["active", "removed"] = "active"
    ingested_from: str | None = None
    blocked_by: str | None = None
    blocked_by_reason: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    permissions: EntityPermissionsOut | None = None


class ApiSummaryOut(CamelModel):
    """The owning API's identity, carried alongside a cross-API Endpoint/
    Operation search result — a Query/Event step's snapshot needs exactly this much to render its
    secondary line without a further fetch."""

    ref: str
    name: str
    title: str


# --- Endpoint ---
#
# Endpoint is plugin-owned child data, not a registered Entity Kind, so it
# has no `*In`/`*Patch` schemas here — only read shapes (no self-service
# create/edit API). `request`/`responses` are stored as
# provisional JSON (`ApiEndpoint.request`/`.responses` docstring) with no
# contract beyond what these read models expose — the models below *are*
# that contract.

EndpointMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
EndpointStatus = Literal["active", "removed"]
EndpointParameterLocation = Literal["path", "query", "header"]


class ExternalDocsOut(CamelModel):
    """`{description?, url}` — the AsyncAPI/OpenAPI External Documentation
    Object shape, reused as-is for `OperationOut.external_docs` and
    `EndpointOut.external_docs`."""

    description: str = ""
    url: str


class EndpointSecurityOut(CamelModel):
    """One resolved entry of `EndpointOut.security` — a security scheme's
    `type` (and, for `http`-type schemes, its `scheme`), not the raw
    spec-author-chosen scheme name."""

    type: str
    scheme: str | None = None


class EndpointSchemaOut(CamelModel):
    """A JSON-Schema-like type descriptor for a parameter/body/response value
    — a provisional shape owned entirely by this plugin (mirrors
    `DatabaseSchema.parsed_schema`'s precedent), not a JSON Schema
    implementation. Covers exactly the shapes the Request/Response tab schema
    viewer needs: object/array/string/integer/number/
    boolean, `enum`, `nullable`, and `$ref`, with `properties`/`items`
    nesting recursively for expandable/collapsible display.
    """

    type: (
        Literal["object", "array", "string", "integer", "number", "boolean"] | None
    ) = None
    ref: str | None = Field(default=None, alias="$ref")
    format: str = ""
    enum: list[str | int | float | bool] | None = None
    nullable: bool = False
    description: str = ""
    properties: dict[str, "EndpointSchemaOut"] = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)
    items: "EndpointSchemaOut | None" = None


class EndpointParameterOut(CamelModel):
    name: str
    location: EndpointParameterLocation
    required: bool = False
    description: str = ""
    schema_: EndpointSchemaOut | None = Field(default=None, alias="schema")


class EndpointBodyOut(CamelModel):
    content_type: str = ""
    schema_: EndpointSchemaOut | None = Field(default=None, alias="schema")
    example: Any = None


class EndpointRequestOut(CamelModel):
    parameters: list[EndpointParameterOut] = Field(default_factory=list)
    body: EndpointBodyOut | None = None


class EndpointResponseHeaderOut(CamelModel):
    """One entry of a response's `headers` map —
    mirrors `EndpointParameterOut` minus `name`/`in` (the map key already
    carries the header name, and a response header has no location)."""

    description: str = ""
    schema_: EndpointSchemaOut | None = Field(default=None, alias="schema")


class EndpointResponseOut(CamelModel):
    status_code: str
    description: str = ""
    content_type: str = ""
    schema_: EndpointSchemaOut | None = Field(default=None, alias="schema")
    example: Any = None
    headers: dict[str, EndpointResponseHeaderOut] = Field(default_factory=dict)


class EndpointOut(CamelModel):
    id: UUID
    api_id: UUID
    method: EndpointMethod
    path: str
    operation_id: str
    summary: str
    description: str
    deprecated: bool
    tags: list[str]
    request: EndpointRequestOut
    responses: list[EndpointResponseOut]
    external_docs: ExternalDocsOut | None = None
    security: list[EndpointSecurityOut] = Field(default_factory=list)
    status: EndpointStatus
    created_at: datetime
    updated_at: datetime


class ApiEndpointsPath(BaseModel):
    api_id: UUID


class ApiEndpointPath(BaseModel):
    api_id: UUID
    id: UUID


class ApiEndpointListQuery(BaseModel):
    method: EndpointMethod | None = None
    tag: str | None = None
    search: str | None = None
    deprecated: bool | None = None
    status: EndpointStatus = "active"


# --- Endpoint search ---
#
# Cross-API, `status="active"`-only search backing the Flow "Add Step"
# Query picker — a flat command-palette lookup, unlike
# `ApiEndpointListController`'s per-API list above.


class ApiEndpointSearchQuery(BaseModel):
    search: str = ""
    page: int = 1
    page_size: int = Field(default=20, le=100)


class EndpointSearchResultOut(CamelModel):
    endpoint: EndpointOut
    api: ApiSummaryOut


# --- Service <-> Endpoint dependency ---------------------------------------------------
#
# `ServiceEndpointUsage` is a bespoke, plugin-owned link, not routed through
# the generic entity-relations system, so its read/write shapes live here
# rather than reusing `RelationOut`/`ListFilters`.

EndpointServiceSort = Literal["service", "team"]
SortDirection = Literal["asc", "desc"]


class ServiceSummaryOut(CamelModel):
    """The subset of a linked Service's `CatalogEntity` fields the Linked
    Services tab/consumers graph need — "team" is the Service's own `owner`
    (every kind's `owner` is its owning Group), not a
    separate concept."""

    id: UUID
    ref: str
    name: str
    title: str
    team: str
    team_id: UUID
    team_name: str


class EndpointServiceOut(CamelModel):
    """One row of `GET /api/endpoints/{endpointId}/services` — a
    `ServiceEndpointUsage` link projected with its Service's summary."""

    id: UUID
    service: ServiceSummaryOut
    linked_at: datetime


class EndpointServiceLinkIn(CamelModel):
    service_id: UUID


class EndpointServiceLinkOut(CamelModel):
    """Response for `POST /api/endpoints/{endpointId}/services` (the
    `apiRelationCreated` flag)."""

    id: UUID
    service: ServiceSummaryOut
    linked_at: datetime
    api_relation_created: bool


class EndpointConsumerSummaryOut(CamelModel):
    id: UUID
    method: EndpointMethod
    path: str
    status: EndpointStatus


class EndpointConsumersOut(CamelModel):
    """The compact consumers-graph data contract — kept forward-compatible with a future full-screen
    explorer, so this returns every linked Service
    unpaginated; the ≤12-node cap is a display concern the frontend applies
    """

    endpoint: EndpointConsumerSummaryOut
    services: list[ServiceSummaryOut]


class EndpointServicesPath(BaseModel):
    endpoint_id: UUID


class EndpointServicePath(BaseModel):
    endpoint_id: UUID
    service_id: UUID


class EndpointServicesQuery(BaseModel):
    search: str | None = None
    team_id: UUID | None = None
    sort: EndpointServiceSort = "service"
    order: SortDirection = "asc"
    page: int = 1
    page_size: int = Field(default=20, le=100)


# --- Operation -
#
# Like `Endpoint`, `Operation` is plugin-owned child data, not a registered
# Entity Kind, so it has no `*In`/`*Patch` schemas — only read shapes
# (no self-service create/edit API).

OperationDirection = Literal["send", "receive"]
OperationStatus = Literal["active", "removed"]
OperationRole = Literal["publisher", "subscriber"]


class OperationMessageOut(CamelModel):
    """One message shape carried by an Operation's channel — a provisional,
    plugin-owned JSON shape (`ApiOperation.message` docstring) reusing
    `EndpointSchemaOut` for its payload schema (the Message tab
    reuses `EndpointSchemaViewer`'s type support)."""

    name: str = ""
    title: str = ""
    summary: str = ""
    content_type: str = ""
    schema_: EndpointSchemaOut | None = Field(default=None, alias="schema")
    example: Any = None
    headers: EndpointSchemaOut | None = None


class OperationProviderOut(CamelModel):
    """The Operation's API document-owner Service (found via the API's
    `apiProvidedBy` relation), with its role implied purely from the
    Operation's `direction` — never a stored
    `ServiceOperationUsage` row."""

    service: ServiceSummaryOut
    role: OperationRole


class OperationOut(CamelModel):
    id: UUID
    api_id: UUID
    channel_address: str
    channel_protocol: str
    direction: OperationDirection
    operation_key: str
    operation_id: str
    summary: str
    description: str
    tags: list[str]
    messages: list[OperationMessageOut]
    external_docs: ExternalDocsOut | None = None
    status: OperationStatus
    deprecated: bool
    provider: OperationProviderOut | None = None
    created_at: datetime
    updated_at: datetime


class ApiOperationsPath(BaseModel):
    api_id: UUID


class ApiOperationPath(BaseModel):
    api_id: UUID
    id: UUID


class ApiOperationListQuery(BaseModel):
    direction: OperationDirection | None = None
    tag: str | None = None
    search: str | None = None
    status: OperationStatus = "active"


# --- Operation search --
#
# Cross-API, `status="active"`-only search backing the Flow "Add Step"
# Event picker — mirrors the Endpoint search above exactly.


class ApiOperationSearchQuery(BaseModel):
    search: str = ""
    page: int = 1
    page_size: int = Field(default=20, le=100)


class OperationSearchResultOut(CamelModel):
    operation: OperationOut
    api: ApiSummaryOut


# --- Service <-> Operation dependency ---------------------------------------------------
#
# `ServiceOperationUsage` is a bespoke, plugin-owned link, not routed through
# the generic entity-relations system — same rationale as
# `ServiceEndpointUsage` above, plus an explicit `role` neither the link nor
# its query shape can borrow from `Endpoint`'s precedent (`direction` and
# `role` answer different questions).

OperationServiceSort = Literal["service", "team"]


class OperationServiceOut(CamelModel):
    """One row of `GET /api/operations/{operationId}/services` — a
    `ServiceOperationUsage` link projected with its Service's summary and
    role."""

    id: UUID
    service: ServiceSummaryOut
    role: OperationRole
    linked_at: datetime


class OperationServiceLinkIn(CamelModel):
    service_id: UUID
    role: OperationRole


class OperationServiceLinkOut(CamelModel):
    """Response for `POST /api/operations/{operationId}/services`. Unlike
    `EndpointServiceLinkOut`, there is no `apiRelationCreated` flag — linking
    a Service to an Operation has no `ComponentDetails` side effect."""

    id: UUID
    service: ServiceSummaryOut
    role: OperationRole
    linked_at: datetime


class OperationConsumerSummaryOut(CamelModel):
    id: UUID
    channel_address: str
    channel_protocol: str
    direction: OperationDirection
    status: OperationStatus


class OperationConsumerParticipantOut(CamelModel):
    """One publisher/subscriber node in the channel-scoped compact graph
    either a document-owner's implied role or an
    explicit `ServiceOperationUsage` link, deduplicated by (service, role)
    across every `ApiOperation` sharing the channel."""

    service: ServiceSummaryOut
    role: OperationRole


class OperationConsumersOut(CamelModel):
    """The compact consumers-graph data contract, aggregated by
    `channel_address` rather than by the single Operation row — `participants` spans every `ApiOperation` sharing that
    channel, not just this operation's own direct links."""

    operation: OperationConsumerSummaryOut
    participants: list[OperationConsumerParticipantOut]


class OperationServicesPath(BaseModel):
    operation_id: UUID


class OperationServicePath(BaseModel):
    operation_id: UUID
    service_id: UUID


class OperationServicesQuery(BaseModel):
    search: str | None = None
    team_id: UUID | None = None
    role: OperationRole | None = None
    sort: OperationServiceSort = "service"
    order: SortDirection = "asc"
    page: int = 1
    page_size: int = Field(default=20, le=100)


class OperationServiceDeleteQuery(BaseModel):
    role: OperationRole
