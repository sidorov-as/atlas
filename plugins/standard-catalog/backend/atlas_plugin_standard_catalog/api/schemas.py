"""Pydantic request/response envelope models for the Standard Catalog kinds
(System, Component, Resource, Team/Group, Actor) — split out of
`server.apps.catalog.api.schemas`.

`GroupSpecIn`/`GroupSpecPatch` and `ActorSpecIn`/`ActorSpecPatch` have no
public REST endpoint (Group and User are read-only via
API) — they exist so Django admin (`admin.py`) and, for Actor, the
ingestion pipeline (`atlas_plugin_ingestion`) can route writes through the
core Entity Service like every other kind.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from atlas_plugin_api import (
    ArchitectureRelationshipDeclarationIn,
    CamelModel,
    EntityPermissionsOut,
    MetadataIn,
    MetadataOut,
    MetadataPatch,
    optional_ref_validator,
    ref_list_validator,
    ref_validator,
)
from pydantic import BaseModel, Field, field_validator

# --- System -------------------------------------------------------------


class SystemSpecIn(CamelModel):
    owner: str
    relationships: list[ArchitectureRelationshipDeclarationIn] = Field(
        default_factory=list
    )

    _validate_owner = field_validator("owner")(ref_validator("group"))


class SystemSpecPatch(CamelModel):
    owner: str | None = None

    _validate_owner = field_validator("owner")(optional_ref_validator("group"))


class SystemSpecOut(CamelModel):
    owner: str
    owner_id: UUID


class SystemIn(CamelModel):
    api_version: str = "atlas/v1alpha1"
    kind: Literal["System"] = "System"
    metadata: MetadataIn
    spec: SystemSpecIn


class SystemPatch(CamelModel):
    metadata: MetadataPatch | None = None
    spec: SystemSpecPatch | None = None


class SystemOut(CamelModel):
    id: UUID
    api_version: str
    kind: Literal["System"] = "System"
    metadata: MetadataOut
    spec: SystemSpecOut
    status: Literal["active", "removed"] = "active"
    ingested_from: str | None = None
    blocked_by: str | None = None
    blocked_by_reason: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    permissions: EntityPermissionsOut | None = None


class SystemDocumentLinksQuery(BaseModel):
    q: str | None = None
    page: int = 1
    page_size: int = Field(default=20, le=100)


# --- Component ------------------------------------------------------------

ComponentType = Literal["service", "website", "library", "worker"]
ComponentLifecycle = Literal["experimental", "production", "deprecated"]


class ComponentSpecIn(CamelModel):
    type: ComponentType
    lifecycle: ComponentLifecycle
    owner: str
    system: str
    provides_apis: list[str] = Field(default_factory=list)
    consumes_apis: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    relationships: list[ArchitectureRelationshipDeclarationIn] = Field(
        default_factory=list
    )

    _validate_owner = field_validator("owner")(ref_validator("group"))
    _validate_system = field_validator("system")(ref_validator("system"))
    _validate_provides_apis = field_validator("provides_apis")(
        ref_list_validator("api")
    )
    _validate_consumes_apis = field_validator("consumes_apis")(
        ref_list_validator("api")
    )
    _validate_depends_on = field_validator("depends_on")(ref_list_validator("resource"))


class ComponentSpecPatch(CamelModel):
    type: ComponentType | None = None
    lifecycle: ComponentLifecycle | None = None
    owner: str | None = None
    system: str | None = None
    provides_apis: list[str] | None = None
    consumes_apis: list[str] | None = None
    depends_on: list[str] | None = None

    _validate_owner = field_validator("owner")(optional_ref_validator("group"))
    _validate_system = field_validator("system")(optional_ref_validator("system"))
    _validate_provides_apis = field_validator("provides_apis")(
        ref_list_validator("api")
    )
    _validate_consumes_apis = field_validator("consumes_apis")(
        ref_list_validator("api")
    )
    _validate_depends_on = field_validator("depends_on")(ref_list_validator("resource"))


class ComponentSpecOut(CamelModel):
    type: ComponentType
    lifecycle: ComponentLifecycle
    owner: str
    owner_id: UUID
    system: str
    system_id: UUID | None
    provides_apis: list[str]
    consumes_apis: list[str]
    depends_on: list[str]


class ComponentIn(CamelModel):
    api_version: str = "atlas/v1alpha1"
    kind: Literal["Component"] = "Component"
    metadata: MetadataIn
    spec: ComponentSpecIn


class ComponentPatch(CamelModel):
    metadata: MetadataPatch | None = None
    spec: ComponentSpecPatch | None = None


class ComponentOut(CamelModel):
    id: UUID
    api_version: str
    kind: Literal["Component"] = "Component"
    metadata: MetadataOut
    spec: ComponentSpecOut
    status: Literal["active", "removed"] = "active"
    ingested_from: str | None = None
    blocked_by: str | None = None
    blocked_by_reason: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    permissions: EntityPermissionsOut | None = None


# --- Resource ---------------------------------------------------------------

ResourceType = Literal["database", "cache", "bucket", "queue", "cluster"]


class ResourceSpecIn(CamelModel):
    type: ResourceType
    owner: str
    system: str | None = None
    relationships: list[ArchitectureRelationshipDeclarationIn] = Field(
        default_factory=list
    )

    _validate_owner = field_validator("owner")(ref_validator("group"))
    _validate_system = field_validator("system")(optional_ref_validator("system"))


class ResourceSpecPatch(CamelModel):
    type: ResourceType | None = None
    owner: str | None = None
    system: str | None = None

    _validate_owner = field_validator("owner")(optional_ref_validator("group"))
    _validate_system = field_validator("system")(optional_ref_validator("system"))


class ResourceSpecOut(CamelModel):
    type: ResourceType
    owner: str
    owner_id: UUID
    system: str | None = None
    system_id: UUID | None = None


class ResourceIn(CamelModel):
    api_version: str = "atlas/v1alpha1"
    kind: Literal["Resource"] = "Resource"
    metadata: MetadataIn
    spec: ResourceSpecIn


class ResourcePatch(CamelModel):
    metadata: MetadataPatch | None = None
    spec: ResourceSpecPatch | None = None


class ResourceOut(CamelModel):
    id: UUID
    api_version: str
    kind: Literal["Resource"] = "Resource"
    metadata: MetadataOut
    spec: ResourceSpecOut
    status: Literal["active", "removed"] = "active"
    ingested_from: str | None = None
    blocked_by: str | None = None
    blocked_by_reason: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    permissions: EntityPermissionsOut | None = None


# --- Group / Actor (admin-managed; Actor also ingestible) -----------------

GroupType = Literal["team", "business-unit", "product-area", "root"]


class MembershipGrantOut(CamelModel):
    id: int
    source_kind: Literal["manual", "provider"]
    provider_id: str | None = None
    source_id: str | None = None
    subject: str | None = None
    external_key: str | None = None
    legacy_unclassified: bool
    created_at: datetime
    last_confirmed_at: datetime
    expires_at: datetime | None = None
    applicable: bool


class EffectiveMembershipOut(CamelModel):
    entity: str
    effective: bool
    grants: list[MembershipGrantOut]


class GroupSpecIn(CamelModel):
    type: GroupType
    members: list[str] = Field(default_factory=list)

    _validate_members = field_validator("members")(ref_list_validator("user"))


class GroupSpecPatch(CamelModel):
    type: GroupType | None = None
    members: list[str] | None = None

    _validate_members = field_validator("members")(ref_list_validator("user"))


class GroupSpecOut(CamelModel):
    type: GroupType
    members: list[str]
    membership_grants: list[EffectiveMembershipOut] = Field(default_factory=list)


class GroupOut(CamelModel):
    id: UUID
    api_version: str = "atlas/v1alpha1"
    kind: Literal["Group"] = "Group"
    metadata: MetadataOut
    spec: GroupSpecOut
    capabilities: list[str] = Field(default_factory=list)


class ActorSpecIn(CamelModel):
    display_name: str = ""
    email: str = ""


class ActorSpecPatch(CamelModel):
    display_name: str | None = None
    email: str | None = None


class ActorProfileOut(CamelModel):
    display_name: str
    email: str


class ActorSpecOut(CamelModel):
    member_of: list[str]
    membership_grants: list[EffectiveMembershipOut] = Field(default_factory=list)
    profile: ActorProfileOut


class ActorOut(CamelModel):
    """Wire `kind`/route stay `"User"` even though the
    underlying Python model is `ActorDetails` — see `models/actor.py`."""

    id: UUID
    api_version: str = "atlas/v1alpha1"
    kind: Literal["User"] = "User"
    metadata: MetadataOut
    spec: ActorSpecOut
    capabilities: list[str] = Field(default_factory=list)


class ActorIn(CamelModel):
    """Ingestion-manifest shape for a `catalog-info.yaml` `kind: User` document
    (Actor becomes ingestible; Team does not)."""

    api_version: str = "atlas/v1alpha1"
    kind: Literal["User"] = "User"
    metadata: MetadataIn
    spec: ActorSpecIn
