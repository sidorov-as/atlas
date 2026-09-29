"""Pydantic request/response envelope models for Flow — split out of
`server.apps.catalog.api.schemas`.
"""

from typing import Literal

from atlas_plugin_api import (
    CamelModel,
    name_validator,
    optional_name_validator,
    optional_ref_validator,
    ref_validator,
)
from pydantic import BaseModel, Field, field_validator

from ..models import StepValidationError, validate_steps

__all__ = [
    "FlowIn",
    "FlowListFilters",
    "FlowOut",
    "FlowPatch",
    "FlowPath",
    "FlowPermissionsOut",
]


def _validate_flow_steps(steps: list[dict]) -> list[dict]:
    try:
        validate_steps(steps)
    except StepValidationError as exc:
        raise ValueError(str(exc)) from exc
    return steps


LayoutDirection = Literal["LAYOUT_LEFT_RIGHT", "LAYOUT_TOP_DOWN"]
LayoutEngine = Literal["dagre", "elk"]

# Generous DoS-prevention bounds,
# matching the shared metadata envelope's `description`/`documentation`
# limits (`atlas_plugin_api.schemas`) for consistency across plugins.
_DESCRIPTION_MAX_LENGTH = 4096
_DOCUMENTATION_MAX_LENGTH = 1024 * 1024  # 1 MiB
_STEPS_MAX_ITEMS = 500


class FlowIn(CamelModel):
    system: str
    name: str
    description: str = Field(default="", max_length=_DESCRIPTION_MAX_LENGTH)
    documentation: str = Field(default="", max_length=_DOCUMENTATION_MAX_LENGTH)
    steps: list[dict] = Field(default_factory=list, max_length=_STEPS_MAX_ITEMS)
    autolayout_enabled: bool = True
    layout_direction: LayoutDirection = "LAYOUT_LEFT_RIGHT"
    layout_engine: LayoutEngine = "dagre"

    _validate_system = field_validator("system")(ref_validator("system"))
    _validate_name = field_validator("name")(name_validator())
    _validate_steps = field_validator("steps")(_validate_flow_steps)


class FlowPatch(CamelModel):
    system: str | None = None
    name: str | None = None
    description: str | None = Field(default=None, max_length=_DESCRIPTION_MAX_LENGTH)
    documentation: str | None = Field(
        default=None, max_length=_DOCUMENTATION_MAX_LENGTH
    )
    steps: list[dict] | None = Field(default=None, max_length=_STEPS_MAX_ITEMS)
    autolayout_enabled: bool | None = None
    layout_direction: LayoutDirection | None = None
    layout_engine: LayoutEngine | None = None

    _validate_system = field_validator("system")(optional_ref_validator("system"))
    _validate_name = field_validator("name")(optional_name_validator())

    @field_validator("steps")
    @classmethod
    def _validate_steps(cls, value: list[dict] | None) -> list[dict] | None:
        return value if value is None else _validate_flow_steps(value)


class FlowPermissionsOut(CamelModel):
    """What the requesting user may do with one Flow. Edit and delete share a
    single permission (`atlas.flows.flow.edit`, checked against the Flow's
    system). A UI hint only; the write endpoints re-check."""

    can_edit: bool


class FlowOut(CamelModel):
    id: int
    system: str
    name: str
    description: str
    documentation: str
    steps: list[dict]
    autolayout_enabled: bool
    layout_direction: LayoutDirection
    layout_engine: LayoutEngine
    # Step id -> {'status': 'active'|'removed', 'deprecated': bool}, computed
    # at read time from the live Endpoint/Operation/CatalogEntity a step's
    # `query_ref`/`event_ref`/`entity_ref` resolves to — never stored on
    # `Flow`, never a replacement for the step's own ref snapshot/string
    # (covers `entity_ref` and `flow_ref` too).
    # Absent entries mean "no live status" — ref not present, plugin not
    # installed (query_ref/event_ref only), or the referenced entity no
    # longer resolves at all (e.g. purged).
    ref_status: dict[str, dict] = Field(default_factory=dict)
    permissions: FlowPermissionsOut | None = None


class FlowListFilters(BaseModel):
    system: str | None = None
    team: str | None = None
    q: str | None = None
    page: int = 1
    page_size: int = Field(default=20, le=100)
    sort: Literal["name", "-name"] = "name"


class FlowPath(BaseModel):
    id: int
