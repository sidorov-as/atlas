"""Test helpers for constructing `CatalogEntity` + `*Details` rows directly.

The single-identity model split what used to be one row per kind
(`System.objects.create(...)`) into a `CatalogEntity` identity row plus a
kind-specific `*Details` row. These helpers keep white-box test setup
(constructing entities directly via the ORM, not through the HTTP API) at
roughly the same call-site size as before.
"""

from atlas_plugin_apis.models import ApiDetails
from atlas_plugin_standard_catalog.models import (
    ActorDetails,
    ComponentDetails,
    GroupDetails,
    ResourceDetails,
    SystemDetails,
)

from server.apps.catalog.models import (
    KIND_ACTOR,
    KIND_API,
    KIND_COMPONENT,
    KIND_GROUP,
    KIND_RESOURCE,
    KIND_SYSTEM,
    CatalogEntity,
    PurgeGrant,
)


def create_group(*, name, type="team", **kwargs):
    entity = CatalogEntity.objects.create(kind=KIND_GROUP, name=name, **kwargs)
    GroupDetails.objects.create(entity=entity, type=type)
    return entity


def create_system(*, name, owner, **kwargs):
    entity = CatalogEntity.objects.create(
        kind=KIND_SYSTEM, name=name, owner=owner, **kwargs
    )
    SystemDetails.objects.create(entity=entity)
    return entity


def create_resource(*, name, owner, type="database", system=None, **kwargs):
    entity = CatalogEntity.objects.create(
        kind=KIND_RESOURCE, name=name, owner=owner, **kwargs
    )
    ResourceDetails.objects.create(entity=entity, type=type, system=system)
    return entity


def create_api(*, name, owner, system, type="openapi", **kwargs):
    entity = CatalogEntity.objects.create(
        kind=KIND_API, name=name, owner=owner, **kwargs
    )
    ApiDetails.objects.create(entity=entity, type=type, system=system)
    return entity


def create_component(
    *,
    name,
    owner,
    system,
    type="service",
    lifecycle="production",
    provides_apis=(),
    consumes_apis=(),
    depends_on=(),
    **kwargs,
):
    entity = CatalogEntity.objects.create(
        kind=KIND_COMPONENT, name=name, owner=owner, **kwargs
    )
    details = ComponentDetails.objects.create(
        entity=entity, type=type, lifecycle=lifecycle, system=system
    )
    if provides_apis:
        details.provides_apis.set(provides_apis)
    if consumes_apis:
        details.consumes_apis.set(consumes_apis)
    if depends_on:
        details.depends_on.set(depends_on)
    return entity


def create_actor(*, name, display_name="", email="", account=None, **kwargs):
    entity = CatalogEntity.objects.create(kind=KIND_ACTOR, name=name, **kwargs)
    ActorDetails.objects.create(
        entity=entity, display_name=display_name, email=email, account=account
    )
    return entity


def create_purge_grant(*, group, grantee, granted_by=None):
    """A `PurgeGrant` row (scoped per owner-Group) — a first-party test-fixture
    builder, not a published contract type, mirroring this module's other
    `create_*` helpers (`ALLOWED_CORE_TEST_SUBMODULES`,
    `server.apps.plugins.tests.test_import_boundaries`) so a plugin's own
    Purge tests don't need to import `PurgeGrant` directly."""
    return PurgeGrant.objects.create(
        group=group, grantee=grantee, granted_by=granted_by
    )
