"""Operation-consumer aggregation shared by `api.views.OperationConsumersController` and
`extension_points.get_operation_consumers()` — kept out of `api/` so the extension point never
imports a controller module."""

from atlas_plugin_api import CatalogEntity, entity_relations, get_catalog_entity_model

from .models import ApiOperation, ServiceOperationUsage


def operation_provider_service(api: CatalogEntity) -> CatalogEntity | None:
    """The API document's own owning Service, found via its `apiProvidedBy`
    relation — `None` if the API has no declared provider."""
    provider_relation = next(
        (
            relation
            for relation in entity_relations(api)
            if relation[0] == "apiProvidedBy"
        ),
        None,
    )
    if provider_relation is None:
        return None
    _predicate, _ref, _kind, provider_id = provider_relation
    return (
        get_catalog_entity_model()
        .objects.select_related("owner", "component_details__system")
        .get(pk=provider_id)
    )


def channel_participants(
    operations: list[ApiOperation],
) -> list[tuple[CatalogEntity, str]]:
    """Every `(service, role)` publisher/subscriber for a channel, aggregated across every
    `ApiOperation` sharing it — each operation's own
    document-owner implied role, plus every explicit `ServiceOperationUsage`
    row, deduplicated by (service, role) since the same Service can
    independently reach the same role from more than one contributing
    operation."""
    apis_by_id = {}
    for operation in operations:
        apis_by_id.setdefault(operation.api_id, operation.api)
    providers = {
        api_id: operation_provider_service(api) for api_id, api in apis_by_id.items()
    }
    seen: set[tuple] = set()
    participants: list[tuple[CatalogEntity, str]] = []
    for operation in operations:
        provider = providers[operation.api_id]
        if provider is None:
            continue
        role = (
            ServiceOperationUsage.ROLE_PUBLISHER
            if operation.direction == ApiOperation.DIRECTION_SEND
            else ServiceOperationUsage.ROLE_SUBSCRIBER
        )
        key = (provider.id, role)
        if key in seen:
            continue
        seen.add(key)
        participants.append((provider, role))
    usages = ServiceOperationUsage.objects.filter(
        operation__in=operations,
    ).select_related("service", "service__owner", "service__component_details__system")
    for usage in usages:
        key = (usage.service_id, usage.role)
        if key in seen:
            continue
        seen.add(key)
        participants.append((usage.service, usage.role))
    return participants


GROUP_BY_TEAM = "team"

# Minimum number of matching Services for a team or system to be returned as a group; a lone
# Service stays a plain Service so the client never decides that rule.
MIN_GROUP_SIZE = 2


def group_name(group: CatalogEntity) -> str:
    return group.title or group.name


def group_of(service: CatalogEntity, group_by: str) -> CatalogEntity | None:
    """The team (owner) or system `service` is grouped under, `None` when it has none."""
    if group_by == GROUP_BY_TEAM:
        return service.owner
    return service.component_details.system


def split_participants_by_group(
    participants: list[tuple[CatalogEntity, str]], group_by: str
) -> tuple[dict[str, list[tuple[CatalogEntity, int]]], list[tuple[CatalogEntity, str]]]:
    """Splits ordered `participants` into per-role groups and the participants left outside them.

    Groups are `{role: [(group entity, size)]}` for every team or system holding at least
    `MIN_GROUP_SIZE` participants of that role, ordered by name then id; the remaining list keeps
    the input order. A team can appear under both roles with different sizes."""
    members: dict[tuple[str, object], list[CatalogEntity]] = {}
    group_entities: dict[object, CatalogEntity] = {}
    for service, role in participants:
        group = group_of(service, group_by)
        if group is None:
            continue
        group_entities[group.id] = group
        members.setdefault((role, group.id), []).append(service)
    listed = {
        key for key, services in members.items() if len(services) >= MIN_GROUP_SIZE
    }
    groups: dict[str, list[tuple[CatalogEntity, int]]] = {}
    for role, group_id in listed:
        groups.setdefault(role, []).append(
            (group_entities[group_id], len(members[(role, group_id)]))
        )
    for entries in groups.values():
        entries.sort(key=lambda entry: (group_name(entry[0]), str(entry[0].id)))
    remaining = [
        (service, role)
        for service, role in participants
        if (group := group_of(service, group_by)) is None
        or (role, group.id) not in listed
    ]
    return groups, remaining
