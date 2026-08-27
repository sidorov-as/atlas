import pytest
from server.apps.catalog.tests.factories import create_group, create_system

from atlas_plugin_ingestion.models import RegisteredRepository


@pytest.fixture
def repo(db):
    return RegisteredRepository.objects.create(source_id="test-source", path="org/repo")


@pytest.fixture
def group(db):
    return create_group(name="platform")


@pytest.fixture
def system(db, group):
    return create_system(name="user-management", owner=group)
