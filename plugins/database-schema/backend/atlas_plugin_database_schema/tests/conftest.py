"""Fixtures for this package's own test suite.

This plugin's tests live in a separate directory tree from `backend/`
(`plugins/database-schema/backend/`), so pytest's directory-walk conftest
discovery doesn't inherit `backend/conftest.py`'s fixtures — a small,
self-contained set is defined here instead, matching `atlas_plugin_c4`'s
own `tests/conftest.py`.
"""

import pytest
from django.contrib.auth import get_user_model
from server.apps.catalog.tests.factories import (
    create_actor,
    create_group,
    create_resource,
)


@pytest.fixture
def group(db):
    return create_group(name="platform")


@pytest.fixture
def resource(db, group):
    return create_resource(name="primary-db", owner=group, type="database")


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
