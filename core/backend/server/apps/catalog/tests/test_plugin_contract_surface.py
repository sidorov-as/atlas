"""`atlas_plugin_api`'s base entity type resolves to Core's real
`CatalogEntity` — verified
from Core's side since `atlas_plugin_api` itself cannot import
`server.apps.catalog` (see `atlas_plugin_api.catalog`'s module docstring)."""

import pytest
from atlas_plugin_api import CatalogEntity as CatalogEntityProtocol
from atlas_plugin_api import get_catalog_entity_model
from atlas_plugin_api.catalog import CATALOG_ENTITY_LABEL

from server.apps.catalog.models.base import CatalogEntity
from server.apps.catalog.tests.factories import create_system


def test_get_catalog_entity_model_resolves_to_the_real_model():
    assert get_catalog_entity_model() is CatalogEntity


def test_catalog_entity_label_matches_the_real_model():
    assert (
        CATALOG_ENTITY_LABEL
        == f"{CatalogEntity._meta.app_label}.{CatalogEntity.__name__}"
    )


@pytest.mark.django_db
def test_a_real_catalog_entity_satisfies_the_published_protocol():
    entity = create_system(name="user-management", owner=None)

    assert isinstance(entity, CatalogEntityProtocol)
