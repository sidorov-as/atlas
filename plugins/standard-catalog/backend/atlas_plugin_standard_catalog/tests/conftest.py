"""Fixtures for this package's own test suite.

This plugin's tests live in a separate directory tree from `backend/`
(`plugins/standard-catalog/backend/`), so pytest's directory-walk conftest
discovery doesn't inherit `backend/conftest.py`'s fixtures — a small,
self-contained set is defined here instead, matching this package's status
as an independently testable unit.
"""

import pytest
from django.contrib.auth import get_user_model
from server.apps.catalog.tests.factories import create_group


@pytest.fixture
def group(db):
    return create_group(name="platform")


@pytest.fixture
def superuser_account(db):
    return get_user_model().objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="password123",
    )


@pytest.fixture
def superuser_client(client, superuser_account):
    client.force_login(superuser_account)
    return client
