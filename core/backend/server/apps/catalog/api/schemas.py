"""Pydantic request/response envelope models for the entity CRUD API.

The subset of these every first-party plugin's own CRUD API reuses
(`CamelModel`, `MetadataIn`/`Out`/`Patch`, `ListFilters`, `PageOut`,
`PaginatedOut`, `RelationOut`, `EntityPath`, `AdoptIn`,
`ArchitectureRelationshipDeclarationIn`, `LinkSchema`, and the ref-validator
helpers) is re-exported from `atlas_plugin_api.schemas` — canonical home
moved there, since none of
it needs a concrete `server` import. Kept as same-named re-exports so Core's
own internal call sites (`api/views.py`) don't need to change.

The schemas below stay defined here: no plugin imports them (Tag and the
manually-authored `ArchitectureRelationship` CRUD API are Core-owned —
`server.apps.catalog.api.views`'s module docstring; Flow's moved to
`atlas_plugin_flows.api.schemas`). `id` fields are
`CatalogEntity.id` (a UUID) — stable
and globally comparable across kinds, unlike the old per-kind integer PK.
"""

from typing import Literal
from uuid import UUID

from atlas_plugin_api.schemas import (
    AdoptIn,
    ArchitectureInteractionKind,
    ArchitectureRelationshipDeclarationIn,
    CamelModel,
    EntityPath,
    LinkSchema,
    ListFilters,
    MetadataIn,
    MetadataOut,
    MetadataPatch,
    PageOut,
    PaginatedOut,
    RelationOut,
    optional_ref_validator,
    ref_validator,
)
from pydantic import BaseModel, Field, field_validator

from server.apps.catalog.models.tag import TAG_PALETTE

__all__ = [
    "AdoptIn",
    "ArchitectureInteractionKind",
    "ArchitectureRelationshipDeclarationIn",
    "ArchitectureRelationshipIn",
    "ArchitectureRelationshipOrigin",
    "ArchitectureRelationshipOut",
    "ArchitectureRelationshipPatch",
    "ArchitectureRelationshipPath",
    "ArchitectureRelationshipQuery",
    "CamelModel",
    "CatalogHomeSettingsOut",
    "CatalogHomeSettingsPatch",
    "EntityPath",
    "LinkSchema",
    "ListFilters",
    "MeOut",
    "MetadataIn",
    "MetadataOut",
    "MetadataPatch",
    "PageOut",
    "PaginatedOut",
    "RelationOut",
    "TagOut",
    "TagPatch",
    "TagPath",
]


# --- Catalog Home Settings ------------------------------------------------


class CatalogHomeSettingsOut(CamelModel):
    """The homepage's admin-editable "About this catalog" content."""

    about_markdown: str


class CatalogHomeSettingsPatch(CamelModel):
    about_markdown: str


# --- Me (admin-status) ----------------------------------------------------


class MeOut(CamelModel):
    """Authorization-role signal for the current session

    Kept separate from allauth's own `SessionUser` payload — allauth owns
    authentication identity, not roles.

    `is_read_only` is a presentation signal only — the backend authorization
    guard, not this
    field, is the actual write boundary.
    """

    is_admin: bool
    is_read_only: bool


# --- Architecture Relationship ---------------------------------------------

ArchitectureRelationshipOrigin = Literal["manual", "yaml"]


class ArchitectureRelationshipIn(CamelModel):
    """A directed, manually authored architecture interaction."""

    source: str
    target: str
    label: str = Field(min_length=1, max_length=255)
    technology: str = Field(default="", max_length=255)
    interaction_kind: ArchitectureInteractionKind = "manual"
    tags: list[str] = Field(default_factory=list)

    _validate_source = field_validator("source")(ref_validator(None))
    _validate_target = field_validator("target")(ref_validator(None))


class ArchitectureRelationshipPatch(CamelModel):
    target: str | None = None
    label: str | None = Field(default=None, min_length=1, max_length=255)
    technology: str | None = Field(default=None, max_length=255)
    interaction_kind: ArchitectureInteractionKind | None = None
    tags: list[str] | None = None

    _validate_target = field_validator("target")(optional_ref_validator(None))


class ArchitectureRelationshipOut(CamelModel):
    id: int
    source: str
    source_kind: str
    source_id: UUID
    source_status: str
    source_deprecated: bool
    target: str
    target_kind: str
    target_id: UUID
    target_status: str
    target_deprecated: bool
    label: str
    technology: str
    interaction_kind: ArchitectureInteractionKind
    tags: list[str]
    origin: ArchitectureRelationshipOrigin


class ArchitectureRelationshipQuery(BaseModel):
    source: str

    _validate_source = field_validator("source")(ref_validator(None))


class ArchitectureRelationshipPath(BaseModel):
    id: int


# --- Tag ----------------------------------------------------------------


class TagOut(CamelModel):
    id: int
    name: str
    color: str


class TagPatch(CamelModel):
    color: str

    @field_validator("color")
    @classmethod
    def _validate_color(cls, value: str) -> str:
        if value not in TAG_PALETTE:
            raise ValueError(f"color must be one of {', '.join(TAG_PALETTE)}")
        return value


class TagPath(BaseModel):
    id: int
