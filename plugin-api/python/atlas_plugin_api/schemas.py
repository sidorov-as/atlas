"""Pydantic request/response envelope models shared by the entity CRUD API
(Core publishes its plugin-facing
surface as contract types).

Canonical home for the subset of `server.apps.catalog.api.schemas` every
first-party plugin's own CRUD API actually reuses — previously imported
directly from Core. None of this needs a Django model/metaclass (only
`refs.py`'s `get_catalog_entity_model()`-backed resolution does, several
layers down inside `ref_validator`), so it moves here outright, the same way
`kinds.py` did. `server.apps.catalog.api.schemas` re-exports it for Core's
own internal call sites, and keeps defining the schemas no plugin needs
(`FlowIn`/`FlowPatch`/`FlowOut`, `TagOut`/`TagPatch`/`TagPath`,
`ArchitectureRelationshipIn`/`Patch`/`Out`/`Query`/`Path`,
`CatalogConfigurationOut`) locally.

`CamelModel` maps snake_case field names to the camelCase keys used by the
Backstage-style envelope (`apiVersion`, `dependsOn`, `providesApis`, ...).
Ref-string fields are validated against `refs.py`'s shared resolver so a
dangling reference is rejected at the request-body level.
"""

from collections.abc import Callable
from datetime import datetime
from typing import ClassVar, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from . import refs


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class PageOut[T](CamelModel):
    """camelCase-serializing counterpart to `dmr.pagination.Page` (a plain dataclass, so it
    serializes its `object_list` field verbatim) — the frontend list pages expect `objectList`."""

    number: int
    object_list: list[T]


class PaginatedOut[T](CamelModel):
    """camelCase-serializing counterpart to `dmr.pagination.Paginated`, for the same reason."""

    count: int
    num_pages: int
    per_page: int
    page: PageOut[T]


def ref_validator(expected_kind: str | None) -> Callable[[str], str]:
    def _validate(value: str) -> str:
        try:
            refs.resolve_ref(value, expected_kind=expected_kind)
        except refs.RefError as exc:
            raise ValueError(str(exc)) from exc
        return value

    return _validate


def optional_ref_validator(
    expected_kind: str | None,
) -> Callable[[str | None], str | None]:
    inner = ref_validator(expected_kind)

    def _validate(value: str | None) -> str | None:
        return value if value is None else inner(value)

    return _validate


def ref_list_validator(expected_kind: str) -> Callable[[list[str]], list[str]]:
    inner = ref_validator(expected_kind)

    def _validate(values: list[str]) -> list[str]:
        return [inner(value) for value in values]

    return _validate


_NAME_FORBIDDEN_CHARS = ("/", ":")


def _validate_name(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("name must not be empty")
    if any(char in stripped for char in _NAME_FORBIDDEN_CHARS):
        raise ValueError("name must not contain '/' or ':'")
    return stripped


def name_validator() -> Callable[[str], str]:
    return _validate_name


def optional_name_validator() -> Callable[[str | None], str | None]:
    def _validate(value: str | None) -> str | None:
        return value if value is None else _validate_name(value)

    return _validate


def _relationship_target_validator(value: str) -> str:
    """Check ref syntax only — resolution is deferred to ingestion reconciliation so a
    target defined later in the same multi-document manifest still validates."""
    try:
        refs.parse_ref(value)
    except refs.RefError as exc:
        raise ValueError(str(exc)) from exc
    return value


# Generous, DoS-prevention bounds (chosen generously, not tightly), not
# UX-driven content limits.
_TITLE_MAX_LENGTH = 255  # matches CatalogEntity.title's DB CharField(max_length=255)
_DESCRIPTION_MAX_LENGTH = 4096
_DOCUMENTATION_MAX_LENGTH = 1024 * 1024  # 1 MiB; documentation is Markdown and may be long
_LABELS_MAX_ITEMS = 100
_TAGS_MAX_ITEMS = 100
_LINKS_MAX_ITEMS = 50
_LINK_URL_MAX_LENGTH = 2048
_LINK_TITLE_MAX_LENGTH = 255
_LINK_TYPE_MAX_LENGTH = 64


class LinkSchema(CamelModel):
    url: str = Field(max_length=_LINK_URL_MAX_LENGTH)
    title: str = Field(default="", max_length=_LINK_TITLE_MAX_LENGTH)
    description: str = Field(default="", max_length=_DESCRIPTION_MAX_LENGTH)
    type: str = Field(default="", max_length=_LINK_TYPE_MAX_LENGTH)


ArchitectureInteractionKind = Literal[
    "synchronous", "asynchronous", "data-access", "manual"
]


class ArchitectureRelationshipDeclarationIn(CamelModel):
    """An outgoing `spec.relationships` declaration on a manifest entity."""

    target: str
    label: str = Field(min_length=1, max_length=255)
    technology: str = Field(default="", max_length=255)
    interaction_kind: ArchitectureInteractionKind = "manual"
    tags: list[str] = Field(default_factory=list)

    _validate_target = field_validator("target")(_relationship_target_validator)


class MetadataIn(CamelModel):
    name: str
    title: str = Field(default="", max_length=_TITLE_MAX_LENGTH)
    description: str = Field(default="", max_length=_DESCRIPTION_MAX_LENGTH)
    documentation: str = Field(default="", max_length=_DOCUMENTATION_MAX_LENGTH)
    labels: dict[str, str] = Field(default_factory=dict, max_length=_LABELS_MAX_ITEMS)
    tags: list[str] = Field(default_factory=list, max_length=_TAGS_MAX_ITEMS)
    links: list[LinkSchema] = Field(default_factory=list, max_length=_LINKS_MAX_ITEMS)

    _validate_name = field_validator("name")(name_validator())


class MetadataPatch(CamelModel):
    name: str | None = None
    title: str | None = Field(default=None, max_length=_TITLE_MAX_LENGTH)
    description: str | None = Field(default=None, max_length=_DESCRIPTION_MAX_LENGTH)
    documentation: str | None = Field(default=None, max_length=_DOCUMENTATION_MAX_LENGTH)
    labels: dict[str, str] | None = Field(default=None, max_length=_LABELS_MAX_ITEMS)
    tags: list[str] | None = Field(default=None, max_length=_TAGS_MAX_ITEMS)
    links: list[LinkSchema] | None = Field(default=None, max_length=_LINKS_MAX_ITEMS)

    _validate_name = field_validator("name")(optional_name_validator())


class MetadataOut(CamelModel):
    name: str
    title: str
    description: str
    documentation: str
    labels: dict[str, str]
    tags: list[str]
    tag_colors: dict[str, str] = Field(default_factory=dict)
    links: list[LinkSchema]


class HistoryRecordOut(CamelModel):
    """One `EntityAuditRecord`, as shown on the entity detail page's History
    section (Remove/Revive/Purge are audited and visible on a History tab)."""

    action: Literal["create", "update", "delete", "remove", "revive", "purge"]
    actor: str | None
    timestamp: datetime


class RelationOut(CamelModel):
    predicate: str
    target: str
    target_kind: str
    target_id: UUID
    # Target's current lifecycle status (surface a
    # removed or deprecated target's status) — `active`/`removed`, plus the
    # cosmetic `deprecated` flag (see `atlas_plugin_api.kinds.entity_deprecated`).
    status: str
    deprecated: bool


class AdoptIn(CamelModel):
    """Body for `POST /api/{kind}/{id}/adopt/`.

    `repository` is `"<source_id>/<path>"`, matching
    `RegisteredRepository.__str__`.
    """

    repository: str


class ListFilters(BaseModel):
    __dmr_force_list__: ClassVar[frozenset[str]] = frozenset(("tags",))

    owner: str | None = None
    system: str | None = None
    lifecycle: str | None = None
    type: str | None = None
    q: str | None = None
    tags: list[str] = []
    # List filtering and search: excludes `removed`
    # entities by default; `all` is the explicit, ungated "show removed" opt-in
    # (hidden with an ungated toggle).
    status: Literal["active", "all"] = "active"
    page: int = 1
    page_size: int = Field(default=20, le=100)
    sort: Literal["name", "-name"] = "name"


class EntityPath(BaseModel):
    id: UUID
