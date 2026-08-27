"""Fixtures for this package's own test suite.

This plugin's tests live in a separate directory tree from `backend/`
(`plugins/apis/backend/`), so pytest's directory-walk conftest discovery
doesn't inherit `backend/conftest.py`'s fixtures (see `atlas_plugin_standard_
catalog.tests.conftest`'s docstring for the same note) — a small,
self-contained set is defined here instead.
"""

import pytest
from django.contrib.auth import get_user_model
from server.apps.catalog.tests.factories import create_actor, create_group


@pytest.fixture
def group(db):
    return create_group(name="platform")


@pytest.fixture
def member_account(db):
    return get_user_model().objects.create_user(
        username="member",
        password="password123",
    )


@pytest.fixture
def superuser_account(db):
    return get_user_model().objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="password123",
    )


@pytest.fixture
def member_client(dmr_client, member_account):
    """An authenticated, non-superuser client — exercises the
    unrestricted-if-authenticated `.create`/`.delete` rule
    (`server.apps.catalog.authorization.RBACPolicyEvaluator`), not just the
    superuser bypass."""
    dmr_client.force_login(member_account)
    return dmr_client


@pytest.fixture
def owner_account(db):
    """A member of `group` (unlike `member_account`) — used by
    the Purge Grant tests, where plain
    owner-Group membership must NOT be sufficient for Purge on its own
    (`server.apps.catalog.authorization.has_purge_grant`)."""
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
