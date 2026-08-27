import pytest
from atlas_plugin_apis.models import ApiDetails
from atlas_plugin_standard_catalog.models import (
    ComponentDetails,
    ResourceDetails,
    SystemDetails,
)

from server.apps.catalog.models import (
    KIND_API,
    KIND_COMPONENT,
    KIND_RESOURCE,
    KIND_SYSTEM,
    CatalogEntity,
)


@pytest.fixture
def system(db, group):
    entity = CatalogEntity.objects.create(
        kind=KIND_SYSTEM, name="user-management", owner=group
    )
    SystemDetails.objects.create(entity=entity)
    return entity


@pytest.fixture
def resource(db, group):
    entity = CatalogEntity.objects.create(
        kind=KIND_RESOURCE, name="primary-db", owner=group
    )
    ResourceDetails.objects.create(entity=entity, type="database")
    return entity


@pytest.fixture
def api(db, group, system):
    entity = CatalogEntity.objects.create(
        kind=KIND_API, name="user-api", owner=group
    )
    ApiDetails.objects.create(entity=entity, type="openapi", system=system)
    return entity


@pytest.fixture
def component(db, group, system):
    entity = CatalogEntity.objects.create(
        kind=KIND_COMPONENT, name="user-service", owner=group
    )
    ComponentDetails.objects.create(
        entity=entity, type="service", lifecycle="production", system=system
    )
    return entity
