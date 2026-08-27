"""Shared fixtures for the catalog CRUD/relations/auth/diagram test suites."""

from datetime import UTC, datetime

import pytest
from atlas_plugin_standard_catalog.models import ActorDetails, GroupDetails
from django.contrib.auth import get_user_model
from django.test import Client

from server.apps.catalog.auth_middleware import (
    AUTHENTICATED_AT_KEY,
    POLICY_GENERATION_KEY,
    PRINCIPAL_GENERATION_KEY,
    PROVIDER_KEY,
)
from server.apps.catalog.auth_security import (
    current_policy_generation,
    principal_generation,
)
from server.apps.catalog.models import KIND_ACTOR, KIND_GROUP, CatalogEntity


@pytest.fixture(autouse=True)
def _atlas_metadata_for_force_login(monkeypatch):
    """Model Django's test-only shortcut as a Core-established local session."""

    original = Client.force_login

    def force_login(client, user, backend=None):
        original(client, user, backend=backend)
        session = client.session
        session[PROVIDER_KEY] = "atlas.auth.local"
        session[AUTHENTICATED_AT_KEY] = datetime.now(UTC).timestamp()
        session[POLICY_GENERATION_KEY] = current_policy_generation()
        session[PRINCIPAL_GENERATION_KEY] = principal_generation(user)
        session.save()

    monkeypatch.setattr(Client, "force_login", force_login)


@pytest.fixture
def group(db):
    entity = CatalogEntity.objects.create(kind=KIND_GROUP, name="platform")
    GroupDetails.objects.create(entity=entity, type="team")
    return entity


@pytest.fixture
def other_group(db):
    entity = CatalogEntity.objects.create(kind=KIND_GROUP, name="other-team")
    GroupDetails.objects.create(entity=entity, type="team")
    return entity


@pytest.fixture
def owner_account(db):
    return get_user_model().objects.create_user(
        username="owner", password="password123"
    )  # noqa: S106


@pytest.fixture
def owner_user(owner_account, group):
    entity = CatalogEntity.objects.create(kind=KIND_ACTOR, name="owner")
    ActorDetails.objects.create(entity=entity, account=owner_account)
    group.group_details.members.add(entity)
    return entity


@pytest.fixture
def other_account(db):
    return get_user_model().objects.create_user(
        username="other", password="password123"
    )  # noqa: S106


@pytest.fixture
def other_user(other_account):
    entity = CatalogEntity.objects.create(kind=KIND_ACTOR, name="other")
    ActorDetails.objects.create(entity=entity, account=other_account)
    return entity


@pytest.fixture
def superuser_account(db):
    return get_user_model().objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="password123",  # noqa: S106
    )


@pytest.fixture
def owner_client(dmr_client, owner_user):
    dmr_client.force_login(owner_user.actor_details.account)
    return dmr_client


@pytest.fixture
def other_client(dmr_client, other_user):
    dmr_client.force_login(other_user.actor_details.account)
    return dmr_client


@pytest.fixture
def superuser_client(dmr_client, superuser_account):
    dmr_client.force_login(superuser_account)
    return dmr_client
