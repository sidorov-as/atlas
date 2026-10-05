from collections.abc import Callable
from typing import ClassVar

from atlas_plugin_api import (
    CATALOG_ENTITY_LABEL,
    CatalogEntity,
    PurgeReference,
    RefError,
    entity_deprecated,
    resolve_ref,
)
from django.apps import apps as django_apps
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import URLValidator
from django.db import models


class StepValidationError(ValueError):
    """A Flow's `steps` array failed entity-ref resolution or the acyclic-transition-graph rule."""


LABEL_THEMES = frozenset({"success", "danger", "warning", "info", "utility", "normal"})
"""Gravity UI `Label` theme tokens a non-entity Step node's `label_theme` may take."""

_LINK_URL_VALIDATOR = URLValidator(schemes=["http", "https"])
"""A Link step's `link_url` is author-supplied and later rendered as a clickable `<a href>`
restricted to http(s) so a `javascript:` or
other unexpected scheme can never be stored, not just a well-formedness check."""

QUERY_REF_KEYS = frozenset({"api", "endpoint", "method", "path"})
EVENT_REF_KEYS = frozenset({"api", "operation", "direction", "channel"})
"""Required keys of a step's `query_ref`/`event_ref` snapshot — `api`/`endpoint`/`method`/`path` and `api`/`operation`/`direction`/`channel` respectively."""

REF_OPTIONAL_KEYS = frozenset({"summary"})
"""Optional key on a `query_ref`/`event_ref` snapshot: the picked Endpoint's/Operation's own `summary`
at pick time — feeds the Call/Event
node's card subtitle, same snapshot-not-live-fetch treatment as `method`/`path`/`channel`/`direction`.
Optional (not required, and its value may be an empty string) since an Endpoint/Operation's `summary`
is itself optional — unlike the required keys, an empty `summary` is not a shape error."""


def _validate_ref_shape(
    step_id: str, field_name: str, value: object, expected_keys: frozenset
) -> None:
    """Shape-check a `query_ref`/`event_ref`: a dict with exactly `expected_keys` (each a non-empty
    string) plus, optionally, any of `REF_OPTIONAL_KEYS` (each a string, empty allowed)."""
    if (
        not isinstance(value, dict)
        or not expected_keys <= set(value)
        or not set(value) <= expected_keys | REF_OPTIONAL_KEYS
    ):
        expected = ", ".join(sorted(expected_keys))
        raise StepValidationError(
            f"Step {step_id!r} has an invalid {field_name}: expected non-empty string fields {{{expected}}}",
        )
    if not all(
        isinstance(v, str) and v for k, v in value.items() if k in expected_keys
    ):
        expected = ", ".join(sorted(expected_keys))
        raise StepValidationError(
            f"Step {step_id!r} has an invalid {field_name}: expected non-empty string fields {{{expected}}}",
        )
    if not all(isinstance(v, str) for k, v in value.items() if k in REF_OPTIONAL_KEYS):
        raise StepValidationError(
            f"Step {step_id!r} has an invalid {field_name}: optional field(s) must be strings",
        )


def _validate_step_shape(step: dict) -> None:
    """Validate the optional `position`, `label_theme`, `external_label`, `query_ref`, `event_ref`,
    `flow_ref`, and `link_url` fields."""
    step_id = step["id"]

    position = step.get("position")
    if position is not None and (
        not isinstance(position, dict)
        or set(position) != {"x", "y"}
        or not all(
            isinstance(value, (int, float)) and not isinstance(value, bool)
            for value in position.values()
        )
    ):
        raise StepValidationError(
            f"Step {step_id!r} has an invalid position: expected {{'x': number, 'y': number}}",
        )

    label_theme = step.get("label_theme")
    if label_theme is not None and label_theme not in LABEL_THEMES:
        raise StepValidationError(
            f"Step {step_id!r} has an invalid label_theme: {label_theme!r}",
        )

    query_ref = step.get("query_ref")
    if query_ref is not None:
        _validate_ref_shape(step_id, "query_ref", query_ref, QUERY_REF_KEYS)

    event_ref = step.get("event_ref")
    if event_ref is not None:
        _validate_ref_shape(step_id, "event_ref", event_ref, EVENT_REF_KEYS)

    flow_ref = step.get("flow_ref")
    if flow_ref is not None and (
        isinstance(flow_ref, bool) or not isinstance(flow_ref, int)
    ):
        raise StepValidationError(
            f"Step {step_id!r} has an invalid flow_ref: expected an integer Flow id, got {flow_ref!r}",
        )

    link_url = step.get("link_url")
    if link_url is not None:
        if not isinstance(link_url, str) or not link_url:
            raise StepValidationError(
                f"Step {step_id!r} has an invalid link_url: expected a non-empty string",
            )
        try:
            _LINK_URL_VALIDATOR(link_url)
        except DjangoValidationError as exc:
            raise StepValidationError(
                f"Step {step_id!r} has an invalid link_url: expected a well-formed http(s) URL",
            ) from exc

    if (step.get("entity_ref") or query_ref or event_ref or flow_ref) and (
        step.get("title") or step.get("summary")
    ):
        raise StepValidationError(
            f"Step {step_id!r} has an entity_ref/query_ref/event_ref/flow_ref and cannot also have a "
            f"title or summary — a ref-backed step always renders text derived from the reference "
            f"itself (the referenced entity's live title/description for entity_ref; the snapshotted "
            f"method/path or channel/direction for query_ref/event_ref; the referenced Flow's live "
            f"name/description for flow_ref), never author-typed text",
        )

    present = [
        name
        for name, value in (
            ("entity_ref", step.get("entity_ref")),
            ("external_label", step.get("external_label")),
            ("query_ref", query_ref),
            ("event_ref", event_ref),
            ("flow_ref", flow_ref),
            ("link_url", link_url),
        )
        if value
    ]
    if len(present) > 1:
        raise StepValidationError(
            f"Step {step_id!r} cannot have more than one of entity_ref, external_label, query_ref, "
            f"event_ref, flow_ref, link_url (has {', '.join(present)})",
        )


def _resolve_query_or_event_ref(step_id: str, ref: dict, *, kind: str) -> None:
    """Resolve a `query_ref`/`event_ref`'s `api` field and its `endpoint`/`operation` id
    `api` via the existing `resolve_ref()`,
    `endpoint`/`operation` via `atlas_plugin_apis.extension_points`, guarded by
    `django_apps.is_installed()` so an absent `atlas.apis` raises a clear `StepValidationError`
    rather than an `ImportError` (mirrors `atlas_plugin_standard_catalog.kinds.
    _register_api_delete_guard`'s guard pattern). Cross-checks that the resolved Endpoint/Operation
    belongs to the resolved `api` entity. A `removed` Endpoint/Operation still resolves — the
    `atlas_plugin_apis` resolvers never filter by status.
    """
    id_field, label = (
        ("endpoint", "Endpoint") if kind == "query" else ("operation", "Operation")
    )

    try:
        api_entity = resolve_ref(ref["api"], expected_kind="api")
    except RefError as exc:
        raise StepValidationError(
            f"Step {step_id!r} has a {kind}_ref with an unresolvable api: {exc}",
        ) from exc

    if not django_apps.is_installed("atlas_plugin_apis"):
        raise StepValidationError(
            f"Step {step_id!r} has a {kind}_ref but the APIs plugin (atlas.apis) is not installed",
        )

    from atlas_plugin_apis.extension_points import resolve_endpoint, resolve_operation

    resolver = resolve_endpoint if kind == "query" else resolve_operation
    resolved = resolver(ref[id_field])
    if resolved is None:
        raise StepValidationError(
            f"Step {step_id!r} has a {kind}_ref whose {id_field} does not resolve to any {label}",
        )
    if resolved.api_id != api_entity.id:
        raise StepValidationError(
            f"Step {step_id!r} has a {kind}_ref whose {label} does not belong to api {ref['api']!r}",
        )


def validate_steps(steps: list[dict]) -> None:
    """Validate a Flow's `steps` JSON.

    Checks (in order): every step has a unique `id`; every non-empty
    `entity_ref` resolves via `resolve_ref()`; every non-empty `query_ref`/
    `event_ref` resolves via `atlas_plugin_apis.extension_points`; every non-empty `flow_ref` resolves to an existing `Flow`
    row by id (a `flow_ref` equal to the Flow being saved's own id is
    permitted — a Flow node is a navigation link, not an embedded sub-flow,
    so self-reference is not a cycle concern); every non-empty `link_url` is a well-formed
    absolute `http`/`https` URL; every
    `next_step`/`next_steps` transition targets a step id that exists in
    `steps`; the transitions across `steps` do not form a cycle, including a
    step transitioning to itself (steps form an acyclic transition graph — a
    step id MAY be the target of any number of incoming transitions, so
    branches may diverge and reconverge); an
    optional `position` is a `{x: number, y: number}` object; an optional
    `label_theme` is one of `LABEL_THEMES`; a step does not carry more than
    one of `entity_ref`, `external_label`, `query_ref`, `event_ref`,
    `flow_ref`, `link_url`; and a step with a non-empty `entity_ref`,
    `query_ref`, `event_ref`, or `flow_ref` does not also carry a non-empty
    `title`/`summary`. Raises
    `StepValidationError` on the first violation found; `collect_step_violations`
    reports every violation instead.
    """
    violations = collect_step_violations(steps)
    if violations:
        raise StepValidationError(violations[0])


def collect_step_violations(steps: list[dict]) -> list[str]:
    """Every violation `validate_steps` would find, in the order it would
    find them, instead of only the first — so a client can fix a flow in one
    pass. Empty when `steps` is valid."""
    violations: list[str] = []

    def _collect(check: Callable[[], None]) -> bool:
        try:
            check()
        except StepValidationError as exc:
            violations.append(str(exc))
            return False
        return True

    step_ids: set[str] = set()
    ordered_ids: list[str] = []
    for step in steps:
        step_id = step.get("id")
        if not step_id:
            violations.append("Every step must have an id")
            continue
        if step_id in step_ids:
            violations.append(f"Duplicate step id: {step_id!r}")
        step_ids.add(step_id)
        ordered_ids.append(step_id)

    adjacency: dict[str, list[str]] = {}

    def _register_transition(source_id: str, target_id: str) -> None:
        if target_id not in step_ids:
            raise StepValidationError(
                f"Step {source_id!r} transitions to unknown step id {target_id!r}",
            )
        adjacency.setdefault(source_id, []).append(target_id)

    def _check_entity_ref(step_id: str, entity_ref: str) -> None:
        try:
            resolve_ref(entity_ref)
        except RefError as exc:
            raise StepValidationError(
                f"Step {step_id!r} has an unresolvable entity_ref: {exc}",
            ) from exc

    def _check_flow_ref(step_id: str, flow_ref: int) -> None:
        if not Flow.objects.filter(pk=flow_ref).exists():
            raise StepValidationError(
                f"Step {step_id!r} has a flow_ref that does not resolve to any existing Flow: {flow_ref!r}",
            )

    for step in steps:
        step_id = step.get("id")
        if not step_id:
            continue

        shape_ok = _collect(lambda step=step: _validate_step_shape(step))

        # A malformed ref has no meaningful resolution; only its shape error
        # is reported. Transitions are still checked below.
        entity_ref = step.get("entity_ref") if shape_ok else None
        if entity_ref:
            _collect(lambda s=step_id, r=entity_ref: _check_entity_ref(s, r))

        query_ref = step.get("query_ref") if shape_ok else None
        if query_ref:
            _collect(
                lambda s=step_id, r=query_ref: _resolve_query_or_event_ref(
                    s, r, kind="query"
                )
            )

        event_ref = step.get("event_ref") if shape_ok else None
        if event_ref:
            _collect(
                lambda s=step_id, r=event_ref: _resolve_query_or_event_ref(
                    s, r, kind="event"
                )
            )

        flow_ref = step.get("flow_ref") if shape_ok else None
        if flow_ref:
            _collect(lambda s=step_id, r=flow_ref: _check_flow_ref(s, r))

        next_step = step.get("next_step")
        if next_step:
            _collect(lambda s=step_id, t=next_step["id"]: _register_transition(s, t))

        for transition in step.get("next_steps") or []:
            _collect(lambda s=step_id, t=transition["id"]: _register_transition(s, t))

    _collect(lambda: _check_no_cycles(ordered_ids, adjacency))
    return violations


def _check_no_cycles(step_ids: list[str], adjacency: dict[str, list[str]]) -> None:
    """Raise `StepValidationError` if `adjacency` (step id -> its transition targets)
    contains a cycle, including a step transitioning to itself. Mirrors the
    frontend's `visiting`/`visited` DFS in `flowSteps.ts`'s `validateFlowSteps`.
    """
    visiting: set[str] = set()
    visited: set[str] = set()

    def _visit(step_id: str) -> None:
        if step_id in visiting:
            raise StepValidationError(f"Transition from {step_id!r} introduces a cycle")
        if step_id in visited:
            return
        visiting.add(step_id)
        for target in adjacency.get(step_id, []):
            _visit(target)
        visiting.discard(step_id)
        visited.add(step_id)

    for step_id in step_ids:
        _visit(step_id)


def resolve_step_ref_statuses(steps: list[dict]) -> dict[str, dict]:
    """Read-time (not save-time) resolution of each step's `query_ref`/`event_ref`/`entity_ref`/
    `flow_ref` live status — a step id -> `{'status': ..., 'deprecated': ...}` map
    (or, for `flow_ref`, `{'name': ..., 'description': ...}` — a Flow has no removed/deprecated
    lifecycle of its own, so entry presence alone is the "does it still resolve" signal) covering
    only steps whose ref currently resolves. A step whose ref no longer resolves at all
    (hard-deleted, or purged for `entity_ref`) is simply absent, so a Flow read never fails
    because of a stale/missing reference. For `entity_ref`, the
    same resolved `CatalogEntity` row also supplies `title`/`description` — no extra query, since rendering an entity-backed node now
    depends on the entity's live title/description rather than the step's own (now-removed)
    `title`/`summary`. `flow_ref` resolution follows the same shape, batched in one query
    (`Flow.objects.filter(pk__in=...)`), and is resolved unconditionally — unlike `query_ref`/
    `event_ref` below, it has no dependency on `atlas_plugin_apis` being installed.
    `query_ref`/`event_ref` resolution is batched by kind
    (`resolve_endpoints`/`resolve_operations`, the same `atlas_plugin_apis.extension_points`
    surface — and `django_apps.is_installed()` guard — `_resolve_query_or_event_ref` already
    uses at save time) so a Flow with many such steps costs at most two extra queries, not one
    per step; `entity_ref` resolves one ref string at a time via the shared `resolve_ref`
    (`CatalogEntity` isn't kind-partitioned the way Endpoint/Operation resolution is), and never
    mutates the step's own stored `entity_ref`.

    For an `event_ref` whose Operation resolves, also compares the step's stored
    `direction`/`channel` against the Operation's current `direction`/`channel_address` — an
    Operation's `operation_key` (not those fields) is its upsert identity, so a re-import can
    change them on the same row a Flow already references.
    When they differ, the live values are added under a `live` key on that step's ref-status
    entry, alongside `status`/`deprecated`; when they match, those two keys are simply omitted
    from `live` (presence-based signal).

    Both `query_ref` and `event_ref` additionally compare the step's stored `summary` snapshot
    against the resolved Endpoint's/Operation's current `summary` — unlike `method`/`path` (an Endpoint's own
    upsert identity, so those specifically cannot drift by construction) or `direction`/`channel`
    above, `summary` is an ordinary mutable field on both models with no such guarantee, so it can
    silently drift the same way `event_ref.direction`/`channel` already could. When it differs,
    `live.summary` is added the same presence-based way, independent of whether `direction`/
    `channel` also differ — an Operation can be renamed/redirected without its summary changing,
    or vice versa.
    """
    ref_status: dict[str, dict] = {}

    entity_ref_by_step = {
        step["id"]: step["entity_ref"] for step in steps if step.get("entity_ref")
    }
    for step_id, ref in entity_ref_by_step.items():
        try:
            entity = resolve_ref(ref)
        except RefError:
            continue
        ref_status[step_id] = {
            "status": entity.status,
            "deprecated": entity_deprecated(entity),
            "title": entity.title,
            "description": entity.description,
        }

    flow_ref_by_step = {
        step["id"]: step["flow_ref"] for step in steps if step.get("flow_ref")
    }
    if flow_ref_by_step:
        target_flows_by_id = {
            flow.id: flow
            for flow in Flow.objects.filter(pk__in=flow_ref_by_step.values())
        }
        for step_id, flow_ref in flow_ref_by_step.items():
            target_flow = target_flows_by_id.get(flow_ref)
            if target_flow is None:
                continue
            ref_status[step_id] = {
                "name": target_flow.name,
                "description": target_flow.description,
            }

    if not django_apps.is_installed("atlas_plugin_apis"):
        return ref_status

    from atlas_plugin_apis.extension_points import resolve_endpoints, resolve_operations

    query_ref_by_step = {
        step["id"]: step["query_ref"] for step in steps if step.get("query_ref")
    }
    event_ref_by_step = {
        step["id"]: step["event_ref"] for step in steps if step.get("event_ref")
    }

    endpoints = resolve_endpoints(ref["endpoint"] for ref in query_ref_by_step.values())
    operations = resolve_operations(
        ref["operation"] for ref in event_ref_by_step.values()
    )

    for step_id, query_ref in query_ref_by_step.items():
        endpoint = endpoints.get(str(query_ref["endpoint"]))
        if endpoint is None:
            continue
        status_entry = {"status": endpoint.status, "deprecated": endpoint.deprecated}
        if query_ref.get("summary", "") != endpoint.summary:
            status_entry["live"] = {"summary": endpoint.summary}
        ref_status[step_id] = status_entry
    for step_id, event_ref in event_ref_by_step.items():
        operation = operations.get(str(event_ref["operation"]))
        if operation is None:
            continue
        status_entry = {"status": operation.status, "deprecated": operation.deprecated}
        live: dict[str, str] = {}
        if (
            event_ref["direction"] != operation.direction
            or event_ref["channel"] != operation.channel_address
        ):
            live["direction"] = operation.direction
            live["channel_address"] = operation.channel_address
        if event_ref.get("summary", "") != operation.summary:
            live["summary"] = operation.summary
        if live:
            status_entry["live"] = live
        ref_status[step_id] = status_entry

    return ref_status


class Flow(models.Model):
    """A hand-authored, ordered sequence of steps documenting a cross-system process.

    Not a `CatalogEntity` — no YAML ingestion, no labels/tags/links, no
    `kind:name` ref namespace. `steps` entity refs are
    validated strings only; they aren't stored as FK/M2M and don't feed the
    derived `Relation` table.
    """

    LAYOUT_LEFT_RIGHT = "LAYOUT_LEFT_RIGHT"
    LAYOUT_TOP_DOWN = "LAYOUT_TOP_DOWN"
    LAYOUT_DIRECTION_CHOICES: ClassVar[list] = [
        (LAYOUT_LEFT_RIGHT, "Left-right"),
        (LAYOUT_TOP_DOWN, "Top-down"),
    ]

    LAYOUT_ENGINE_DAGRE = "dagre"
    LAYOUT_ENGINE_ELK = "elk"
    LAYOUT_ENGINE_CHOICES: ClassVar[list] = [
        (LAYOUT_ENGINE_DAGRE, "Dagre"),
        (LAYOUT_ENGINE_ELK, "ELK.js"),
    ]

    system = models.ForeignKey(
        CATALOG_ENTITY_LABEL, on_delete=models.PROTECT, related_name="flows"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    documentation = models.TextField(blank=True)
    steps = models.JSONField(default=list, blank=True)
    # A Flow-level, persisted binary
    # mode (not a per-step "position wins if present" merge) and a persisted,
    # viewer-independent layout direction (not a `localStorage` preference).
    autolayout_enabled = models.BooleanField(default=True)
    layout_direction = models.CharField(
        max_length=32,
        choices=LAYOUT_DIRECTION_CHOICES,
        default=LAYOUT_LEFT_RIGHT,
    )
    # A persisted, per-Flow, shared
    # (not per-viewer) choice of layout algorithm, following the same pattern as
    # `layout_direction`.
    layout_engine = models.CharField(
        max_length=32,
        choices=LAYOUT_ENGINE_CHOICES,
        default=LAYOUT_ENGINE_DAGRE,
    )
    # Audit timestamps. Bulk updates (`QuerySet.update`) bypass `auto_now`, so these are not a
    # reliable sync cursor — search indexing does not depend on them.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Kept on the pre-existing `catalog` app_label (the same
        # technique `ApiDetails` uses) so this
        # physical package move needs no new migration — `catalog`'s
        # existing migration history already created this table.
        app_label = "catalog"
        ordering: ClassVar[list] = ["name"]
        constraints: ClassVar[list] = [
            models.UniqueConstraint(
                fields=["system", "name"], name="catalog_flow_unique_system_name"
            ),
        ]

    def __str__(self) -> str:
        return self.name


def scan_flow_purge_references(entity: CatalogEntity) -> list[PurgeReference]:
    """Purge scanner registered against `atlas_plugin_api.purge` (entity-removal-
    lifecycle spec: "Purge validation scans both FK-backed and ref-string-backed
    references", D8's ref-string blind-spot mitigation) — a Flow step's
    `entity_ref` is a plain string, not a FK/M2M, so
    nothing at the DB level stops purging something a Flow still points at.

    Unlike an M2M reference whose *referencing entity* can itself be `removed`
    (see `atlas_plugin_standard_catalog`'s purge scanners), `Flow` carries no
    `status`/removed concept of its own — a matching `entity_ref` always
    blocks, with no cascade case, matching the "an active Flow step's
    `entity_ref`" case exactly (no
    "a removed Flow" scenario exists to cascade for).
    """
    references = []
    for flow in Flow.objects.all():
        for step in flow.steps:
            if step.get("entity_ref") == entity.ref:
                references.append(
                    PurgeReference(label=f"Flow {flow.name!r}", active=True)
                )
                break
    return references
