"""Request schemas for the diagram endpoints — split out of
`server.apps.catalog.api.schemas`.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from atlas_plugin_api import CamelModel
from pydantic import BaseModel, Field, field_validator, model_validator


class DiagramPath(BaseModel):
    kind: str
    id: UUID


class DiagramQuery(BaseModel):
    view: str | None = None
    format: Literal["svg", "png"] = "svg"
    download: bool = False
    layout: Literal["LAYOUT_TOP_DOWN", "LAYOUT_LEFT_RIGHT", "LAYOUT_LANDSCAPE"] = (
        "LAYOUT_TOP_DOWN"
    )
    show_title: bool = True
    show_legend: bool = True
    show_selected_label: bool = True
    show_person_sprite: bool = True
    show_stereotypes: bool = True
    theme: Literal["light", "dark"] = "light"


CustomViewLevel = Literal["systems", "components"]
CustomViewSelection = Literal["selected", "neighborhood"]
CustomViewDirection = Literal["both", "outgoing", "incoming"]
CustomViewRelationshipSource = Literal["declared", "declared_and_derived"]
CustomViewEntityType = Literal["component", "resource", "api", "actor", "none"]

_COMPONENT_LEVEL_ONLY_TYPES = frozenset({"component", "resource", "api"})


class CustomViewSettings(CamelModel):
    """View settings: the JSON body of the preview endpoint and the stored
    ``settings`` of a saved view.

    ``entities`` are the selected entities (roots in Neighborhood mode).
    ``depth`` is a positive integer or ``"all"``; ``depth`` and ``direction``
    only apply to Neighborhood mode and are dropped in Selected mode, even
    when invalid. ``entity_types`` ``null`` (or omitted) enables every type
    available at the level, actors included; an empty list enables none of
    the optional types. Rendering options and format are not settings: they
    stay query parameters.
    """

    level: CustomViewLevel
    selection: CustomViewSelection
    entities: list[UUID] = Field(default_factory=list)
    depth: int | Literal["all"] | None = None
    direction: CustomViewDirection | None = None
    entity_types: list[CustomViewEntityType] | None = None
    relationships: CustomViewRelationshipSource = "declared"

    @model_validator(mode="before")
    @classmethod
    def _drop_neighborhood_only_fields(cls, data):
        if isinstance(data, dict) and data.get("selection") == "selected":
            return {k: v for k, v in data.items() if k not in {"depth", "direction"}}
        return data

    @field_validator("depth")
    @classmethod
    def _depth_is_positive(cls, value):
        if isinstance(value, int) and value < 1:
            raise ValueError("depth must be a positive integer or 'all'")
        return value

    @model_validator(mode="after")
    def _validate_selection(self):
        if not self.entities:
            raise ValueError("at least one entity is required")
        if len(set(self.entities)) != len(self.entities):
            raise ValueError("entities must be unique")
        if self.selection == "neighborhood":
            if self.depth is None:
                self.depth = 1
            if self.direction is None:
                self.direction = "both"
        if self.entity_types is not None:
            if len(set(self.entity_types)) != len(self.entity_types):
                raise ValueError("entityTypes must be unique")
            if self.level == "systems":
                invalid = _COMPONENT_LEVEL_ONLY_TYPES.intersection(self.entity_types)
                if invalid:
                    raise ValueError(
                        f"entityTypes {sorted(invalid)} are not available at the systems level"
                    )
        return self


class ActorKindOut(BaseModel):
    kind: str
    label: str


class ActorKindsOut(BaseModel):
    items: list[ActorKindOut]


VIEW_NAME_MAX_LENGTH = 255
VIEW_DESCRIPTION_MAX_LENGTH = 4096


class ViewIn(CamelModel):
    name: str = Field(max_length=VIEW_NAME_MAX_LENGTH)
    description: str = Field(default="", max_length=VIEW_DESCRIPTION_MAX_LENGTH)
    settings: CustomViewSettings

    @field_validator("name")
    @classmethod
    def _name_is_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name must not be empty")
        return value


class ViewOut(CamelModel):
    id: UUID
    name: str
    description: str
    settings: CustomViewSettings
    missing_entities: list[UUID]
    created_at: datetime
    updated_at: datetime


class ViewPath(BaseModel):
    id: UUID


class ViewListFilters(BaseModel):
    q: str | None = None
    page: int = 1
    page_size: int = Field(default=20, le=100)
    sort: Literal["name", "-name"] = "name"
