"""Fixtures for this package's own test suite.

This plugin's tests live in a separate directory tree from `backend/`
(`plugins/flows/backend/`), so pytest's directory-walk conftest discovery
doesn't inherit `backend/conftest.py`'s fixtures — a small, self-contained
set is defined here instead, matching `atlas_plugin_c4`'s own
`tests/conftest.py`.

Fixture names are chosen not to collide with another plugin's own
`tests/conftest.py` (e.g. `atlas_plugin_standard_catalog`'s `superuser_client`)
— pytest resolves same-named fixtures across these sibling, non-nested
plugin test trees by conftest registration order, not by directory
proximity, so a shared name can silently shadow a different plugin's
fixture of the same name. `non_member_*` mirrors `atlas_plugin_apis`'s own
`member_*` naming for the same reason.
"""

import pytest
from django.contrib.auth import get_user_model
from server.apps.catalog.tests.factories import (
    create_actor,
    create_component,
    create_group,
    create_system,
)


@pytest.fixture
def group(db):
    return create_group(name="platform")


@pytest.fixture
def foreign_group(db):
    return create_group(name="other-team")


@pytest.fixture
def system(db, group):
    return create_system(name="user-management", owner=group)


@pytest.fixture
def component(db, group, system):
    return create_component(
        name="user-service",
        owner=group,
        system=system,
        type="service",
        lifecycle="production",
    )


@pytest.fixture
def owner_account(db):
    return get_user_model().objects.create_user(
        username="owner",
        password="password123",
    )


@pytest.fixture
def owner_user(owner_account, group):
    entity = create_actor(name="owner", account=owner_account)
    group.group_details.members.add(entity)
    return entity


@pytest.fixture
def owner_client(dmr_client, owner_user):
    dmr_client.force_login(owner_user.actor_details.account)
    return dmr_client


@pytest.fixture
def non_member_account(db):
    return get_user_model().objects.create_user(
        username="non-member",
        password="password123",
    )


@pytest.fixture
def non_member_user(non_member_account):
    return create_actor(name="non-member", account=non_member_account)


@pytest.fixture
def non_member_client(dmr_client, non_member_user):
    dmr_client.force_login(non_member_user.actor_details.account)
    return dmr_client
