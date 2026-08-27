"""Catalog Home Settings ("About this catalog") API tests."""

import pytest

from server.apps.catalog.models import CatalogHomeSettings
from server.apps.catalog.models.catalog_home_settings import (
    DEFAULT_ABOUT_MARKDOWN,
)

pytestmark = pytest.mark.django_db


def test_default_content_present_after_migration_alone():
    instance = CatalogHomeSettings.get_solo()
    assert instance.about_markdown == DEFAULT_ABOUT_MARKDOWN


def test_default_content_present_after_row_is_gone_not_just_after_migration():
    """`manage.py flush` (`seed_booking_demo`'s own flush-and-repopulate step
    included) truncates this table without re-running the `RunPython` data
    migration that originally seeded it — `get_solo()` must still produce
    real content the next time it's called, not an empty row."""
    CatalogHomeSettings.objects.all().delete()

    instance = CatalogHomeSettings.get_solo()

    assert instance.about_markdown == DEFAULT_ABOUT_MARKDOWN


def test_read_allowed_for_any_authenticated_user(owner_client):
    response = owner_client.get("/api/catalog-home-settings/")

    assert response.status_code == 200
    assert response.json() == {"aboutMarkdown": DEFAULT_ABOUT_MARKDOWN}


def test_read_requires_authentication(dmr_client):
    response = dmr_client.get("/api/catalog-home-settings/")

    assert response.status_code == 401


def test_write_rejected_for_non_superuser(owner_client):
    response = owner_client.patch(
        "/api/catalog-home-settings/",
        {"aboutMarkdown": "Nope"},
    )

    assert response.status_code == 403
    assert (
        CatalogHomeSettings.get_solo().about_markdown == DEFAULT_ABOUT_MARKDOWN
    )


def test_write_accepted_for_superuser(superuser_client):
    response = superuser_client.patch(
        "/api/catalog-home-settings/",
        {"aboutMarkdown": "# Welcome"},
    )

    assert response.status_code == 200
    assert response.json() == {"aboutMarkdown": "# Welcome"}
    assert CatalogHomeSettings.get_solo().about_markdown == "# Welcome"
