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
        get_catalog_entity_model().objects.select_related("owner").get(pk=provider_id)
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
    ).select_related("service", "service__owner")
    for usage in usages:
        key = (usage.service_id, usage.role)
        if key in seen:
            continue
        seen.add(key)
        participants.append((usage.service, usage.role))
    return participants
