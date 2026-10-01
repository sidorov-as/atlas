"""`StepIn` and friends: the typed shape of one element of `FlowIn.steps`/
`FlowPatch.steps`, mirroring `plugins/flows/frontend/src/lib/
flowStepSchema.ts`'s JSON Schema field for field.

Before this module existed, `steps` was simply `list[dict]` — valid JSON,
but with no structure an OpenAPI/MCP tool schema could describe, and no
Pydantic-level check of its own. Two independent, real consequences of
that: (1) `create_flow`/`update_flow`'s generated MCP tool schema described
`steps` as a bare array of opaque objects, giving a tool-calling client no
field names, types, or enums to work from; (2) several fields `atlas_plugin_
flows.models._validate_step_shape()` never checked at all — notably `icon`
and `color` — could be set to any garbage value, which saved successfully
and then silently failed to render, with no error ever returned to the
caller.

This module closes both gaps at the type layer. `atlas_plugin_flows.models.
validate_steps()` stays the authority for everything that genuinely needs a
database round-trip — `entity_ref`/`query_ref`/`event_ref`/`flow_ref`
*resolution*, and the transition graph's acyclicity — neither of which a
single step's own shape can decide in isolation; `api.schemas._validate_flow_
steps()` still calls it, unchanged, against this module's `.model_dump()`
output. Every purely structural rule `_validate_step_shape()`/`_validate_ref_
shape()` already enforced (required keys, non-empty strings, the `position`/
`label_theme` shape, the one-ref-field-max rule) is reproduced here instead
of removed from there — those functions stay as *that* module's own,
independently-tested authority for anyone calling `validate_steps()`
directly with a raw `list[dict]` (its own test suite does exactly this), so
by the time a `StepIn`-validated step reaches them, those checks simply
never fire.
"""

from typing import Literal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import URLValidator
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .._gravity_icons import GRAVITY_ICON_NAMES

__all__ = ["EventRefIn", "PositionIn", "QueryRefIn", "StepIn", "TransitionIn"]

# Mirrors `atlas_plugin_flows.models.LABEL_THEMES`/`flowStepSchema.ts`'s
# `LABEL_THEMES`/`STEP_COLORS` constants exactly — a `Literal` (not just a
# runtime check) so the enum shows up for free in the generated OpenAPI/MCP
# tool schema, matching `flowStepSchema.ts`'s own `enum` for both fields.
# Kept as its own tuple here rather than imported from `models.py`, matching
# the frontend's own acknowledged, deliberately-not-DRY precedent
# (`flowStepSchema.ts`: "the two fields' allowed sets are only
# coincidentally identical today, not definitionally the same"). If either
# vocabulary changes, update all three.
_StepLabelTheme = Literal["success", "danger", "warning", "info", "utility", "normal"]
_StepColor = Literal["success", "danger", "warning", "info", "utility", "normal"]

_LINK_URL_VALIDATOR = URLValidator(schemes=["http", "https"])

# The six fields a step may hold at most one of — mirrors `models.py`'s own
# `present = [...]` list in `_validate_step_shape()` exactly, including its
# falsy-means-absent treatment (an empty string/0/None all count as "not
# set", same as `if value` there).
_REF_LIKE_FIELD_NAMES = (
    "entity_ref",
    "external_label",
    "query_ref",
    "event_ref",
    "flow_ref",
    "link_url",
)


def _reject_bool(value: object) -> object:
    """`isinstance(x, bool)` is true for a Python `bool` passed where a
    number is expected (`bool` subclasses `int`) — Pydantic's default,
    non-strict coercion would otherwise silently accept `true`/`false` as
    `1`/`0`. Mirrors `models.py`'s own explicit bool-rejection for `position`
    's `x`/`y`."""
    if isinstance(value, bool):
        # ValueError, not TypeError: a Pydantic validator must raise
        # ValueError/AssertionError for Pydantic to turn it into a
        # ValidationError — a TypeError would propagate uncaught instead.
        raise ValueError("expected a number, not a boolean")  # noqa: TRY004
    return value


class TransitionIn(BaseModel):
    """One entry of a step's `next_step`/`next_steps` — mirrors
    `flowStepSchema.ts`'s `transitionSchema`."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, description="Target step id")
    label: str | None = Field(default=None, description="Transition label (optional)")


class PositionIn(BaseModel):
    """A step's manually-placed canvas position — mirrors `flowStepSchema.ts`
    's `positionSchema`. A step with no `position` autolayouts instead."""

    model_config = ConfigDict(extra="forbid")

    x: float
    y: float

    _reject_bool_x = field_validator("x", mode="before")(_reject_bool)
    _reject_bool_y = field_validator("y", mode="before")(_reject_bool)


class QueryRefIn(BaseModel):
    """A Query step's Endpoint reference snapshot — mirrors
    `flowStepSchema.ts`'s `queryRefSchema` and `models.py`'s
    `QUERY_REF_KEYS`/`REF_OPTIONAL_KEYS`. A point-in-time snapshot, not
    re-derived from the referenced Endpoint at read time."""

    model_config = ConfigDict(extra="forbid")

    api: str = Field(min_length=1, description="Owning API ref, e.g. api:orders-api")
    endpoint: str = Field(min_length=1, description="Endpoint id (UUID)")
    method: str = Field(min_length=1, description="Snapshotted HTTP method")
    path: str = Field(min_length=1, description="Snapshotted path")
    summary: str | None = Field(
        default=None,
        description="Snapshotted Endpoint summary (optional); feeds the node's subtitle",
    )


class EventRefIn(BaseModel):
    """An Event step's Operation reference snapshot — mirrors
    `flowStepSchema.ts`'s `eventRefSchema` and `models.py`'s
    `EVENT_REF_KEYS`/`REF_OPTIONAL_KEYS`."""

    model_config = ConfigDict(extra="forbid")

    api: str = Field(min_length=1, description="Owning API ref, e.g. api:orders-api")
    operation: str = Field(min_length=1, description="Operation id (UUID)")
    direction: str = Field(
        min_length=1, description="Snapshotted direction, e.g. 'send'/'receive'"
    )
    channel: str = Field(min_length=1, description="Snapshotted channel address")
    summary: str | None = Field(
        default=None,
        description="Snapshotted Operation summary (optional); feeds the node's subtitle",
    )


class StepIn(BaseModel):
    """One element of `FlowIn.steps`/`FlowPatch.steps` — see module
    docstring. A step is one of several kinds depending on which of
    `entity_ref`/`external_label`/`query_ref`/`event_ref`/`flow_ref`/
    `link_url` is set (at most one, enforced below) — a plain Step node,
    an out-of-catalog reference, a Query/Event/Flow/Link step, or (with
    none of those) a plain label-only node."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, description="Unique step identifier")
    title: str | None = Field(default=None, description="Display title (optional)")
    summary: str | None = Field(
        default=None, description="Short description (optional)"
    )
    entity_ref: str | None = Field(
        default=None,
        description="Reference to a system/component/resource/api (optional)",
    )
    next_step: TransitionIn | None = Field(
        default=None, description="Single next transition (optional)"
    )
    next_steps: list[TransitionIn] = Field(
        default_factory=list, description="Multiple next transitions (optional)"
    )
    position: PositionIn | None = None
    label_theme: _StepLabelTheme | None = Field(
        default=None,
        description=(
            "Deprecated: replaced by 'color'. Still accepted so an "
            "unmigrated flow keeps validating (optional)"
        ),
    )
    color: _StepColor | None = Field(
        default=None,
        description="Plain Step node color, e.g. 'success'/'danger' (optional)",
    )
    icon: str | None = Field(
        default=None,
        description="Plain Step node icon, a @gravity-ui/icons component name (optional)",
    )
    type_label: str | None = Field(
        default=None,
        description=(
            'Plain Step node chip label; free text, falls back to "Step" '
            "when blank/unset (optional)"
        ),
    )
    external_label: str | None = Field(
        default=None,
        description=(
            "Out-of-catalog reference label; mutually exclusive with "
            "entity_ref, query_ref, and event_ref (optional)"
        ),
    )
    query_ref: QueryRefIn | None = Field(
        default=None,
        description=(
            "Endpoint reference snapshot (Query step); mutually exclusive "
            "with entity_ref, external_label, and event_ref (optional)"
        ),
    )
    event_ref: EventRefIn | None = Field(
        default=None,
        description=(
            "Operation reference snapshot (Event step); mutually exclusive "
            "with entity_ref, external_label, and query_ref (optional)"
        ),
    )
    flow_ref: int | None = Field(
        default=None,
        description=(
            "Reference to another Flow by id (Flow step); mutually "
            "exclusive with every other ref field (optional)"
        ),
    )
    link_url: str | None = Field(
        default=None,
        description="External URL (Link step); mutually exclusive with every other ref field (optional)",
    )

    _reject_bool_flow_ref = field_validator("flow_ref", mode="before")(_reject_bool)

    @field_validator("icon")
    @classmethod
    def _validate_icon(cls, value: str | None) -> str | None:
        if value is not None and value not in GRAVITY_ICON_NAMES:
            raise ValueError(
                f"{value!r} is not a known @gravity-ui/icons component name"
            )
        return value

    @field_validator("link_url")
    @classmethod
    def _validate_link_url(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not value:
            raise ValueError("expected a non-empty string")
        try:
            _LINK_URL_VALIDATOR(value)
        except DjangoValidationError as exc:
            raise ValueError("expected a well-formed http(s) URL") from exc
        return value

    @model_validator(mode="after")
    def _validate_ref_exclusivity(self) -> "StepIn":
        present = [name for name in _REF_LIKE_FIELD_NAMES if getattr(self, name)]
        if len(present) > 1:
            raise ValueError(
                "cannot have more than one of "
                f"{', '.join(_REF_LIKE_FIELD_NAMES)} (has {', '.join(present)})"
            )

        # Mirrors `models.py`'s own `_validate_step_shape()` exactly: only
        # these four ref kinds forbid a title/summary (a ref-backed step
        # always renders text derived from the reference itself) —
        # `external_label`/`link_url` are not included, matching that
        # function's own condition precisely.
        if (self.entity_ref or self.query_ref or self.event_ref or self.flow_ref) and (
            self.title or self.summary
        ):
            raise ValueError(
                "a step with an entity_ref/query_ref/event_ref/flow_ref cannot "
                "also have a title or summary — a ref-backed step always "
                "renders text derived from the reference itself"
            )
        return self
