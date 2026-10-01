"""`atlas_plugin_flows`'s cross-plugin function/registration surface —
mirrors `atlas_plugin_apis.extension_points`'s shape and reason for being:
`FlowService` needs real Django ORM work against the concrete `Flow` model,
which a types-only `contracts.py` structurally can't hold, so this module
publishes:

- `FlowService`, mirroring Core's `EntityService`'s shape (list/get/create/
  update/delete; an `actor` parameter on every write; `get`/`list` raise/
  return plainly rather than needing one — same as `EntityService`; the
  same "not-found is a plain `LookupError`, not a `dmr` `APIError`"
  convention via `contracts.FlowNotFoundError`) — the one path both the
  existing Flow REST controllers (`api.views`) and the new `atlas.mcp`
  plugin call, so the two can never diverge in validation or permission
  checks (flows-plugin spec: "Flow CRUD is available through a published
  FlowService contract").
- `get_flow_service()`, a plain accessor for the process-wide singleton.
  Unlike `atlas_plugin_api.entity_service`'s `bind_entity_service()`/
  `get_entity_service()` pair (needed there because Core can't be imported
  by a plugin), no cross-package registration hand-off is needed here:
  `atlas_plugin_flows` owns both the `Flow` model and this service
  outright, so a dependent plugin imports `get_flow_service()` directly,
  the same way it already imports
  `atlas_plugin_apis.extension_points.resolve_endpoint()`.

A plugin performs Flow operations through `get_flow_service()`, never by
importing `atlas_plugin_flows`'s internal `Flow` model or `api.views`
helpers directly.
"""

from typing import Any

from atlas_plugin_api import (
    KIND_SYSTEM,
    filter_by_search,
    filter_by_system,
    filter_by_team,
    resolve_ref,
)
from django.db.models import QuerySet

from .contracts import FlowIn, FlowNotFoundError, FlowPatch
from .models import Flow
from .permissions import check_flow_write_permission

__all__ = ["FlowService", "get_flow_service"]


class FlowService:
    """The one path both the Flow REST controllers and other plugins use to
    list, read, create, update, or delete a `Flow` — see module docstring.
    Obtained via `get_flow_service()`, never constructed directly.
    """

    def get(self, flow_id: int) -> Flow:
        try:
            return Flow.objects.select_related("system", "system__owner").get(
                pk=flow_id
            )
        except Flow.DoesNotExist:
            raise FlowNotFoundError(str(flow_id)) from None

    def list(
        self,
        *,
        system: str | None = None,
        team: str | None = None,
        search: str | None = None,
    ) -> QuerySet[Flow]:
        """Returns a filtered, unordered, unpaginated queryset — ordering
        and pagination stay the REST list endpoint's own concern (it needs
        the caller-chosen `sort`/`page`/`page_size`), matching how
        `EntityService.list` leaves richer, caller-specific filtering out of
        its own contract.
        """
        queryset = Flow.objects.select_related("system", "system__owner")
        queryset = filter_by_system(queryset, system)
        queryset = filter_by_team(queryset, team)
        queryset = filter_by_search(queryset, search)
        return queryset

    def create(self, *, body: FlowIn, actor: Any) -> Flow:
        instance = Flow()
        instance.system = resolve_ref(body.system, expected_kind=KIND_SYSTEM)
        instance.name = body.name
        instance.description = body.description
        instance.documentation = body.documentation
        # `body.steps` is `list[StepIn]` (typed, for a real OpenAPI/MCP tool
        # schema — see `api.step_schemas`), but the `Flow.steps` JSONField
        # needs plain, natively-JSON-serializable dicts — sparse ones
        # (`exclude_none=True`), matching the shape the web UI's own raw
        # JSON editor has always sent (an unset field is an absent key, not
        # an explicit `null`), which `models.py`'s dict-based checks assume.
        instance.steps = [step.model_dump(exclude_none=True) for step in body.steps]
        instance.autolayout_enabled = body.autolayout_enabled
        instance.layout_direction = body.layout_direction
        instance.layout_engine = body.layout_engine
        check_flow_write_permission(actor, instance.system)
        instance.save()
        return instance

    def update(self, *, flow_id: int, body: FlowPatch, actor: Any) -> Flow:
        instance = self.get(flow_id)
        check_flow_write_permission(actor, instance.system)
        fields = body.model_fields_set
        if "system" in fields:
            instance.system = resolve_ref(body.system, expected_kind=KIND_SYSTEM)
        if "name" in fields:
            instance.name = body.name
        if "description" in fields:
            instance.description = body.description
        if "documentation" in fields:
            instance.documentation = body.documentation
        if "steps" in fields:
            # See `create()`'s own comment: dump typed `StepIn` back to
            # plain dicts for the JSONField. `body.steps` can legitimately
            # be `None` here (an explicit `"steps": null` patch) — preserved
            # as-is rather than coerced to `[]`, matching this field's
            # pre-existing behavior for every other optional field above.
            instance.steps = (
                [step.model_dump(exclude_none=True) for step in body.steps]
                if body.steps is not None
                else None
            )
        if "autolayout_enabled" in fields:
            instance.autolayout_enabled = body.autolayout_enabled
        if "layout_direction" in fields:
            instance.layout_direction = body.layout_direction
        if "layout_engine" in fields:
            instance.layout_engine = body.layout_engine
        instance.save()
        return instance

    def delete(self, *, flow_id: int, actor: Any) -> None:
        instance = self.get(flow_id)
        check_flow_write_permission(actor, instance.system)
        instance.delete()


# Process-wide instance, matching `server.apps.catalog.services.entity_service`'s
# own module-level singleton.
flow_service = FlowService()


def get_flow_service() -> FlowService:
    """Return the process-wide `FlowService` singleton."""
    return flow_service
