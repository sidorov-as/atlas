"""Core's shared entity-controller helpers must not hard-depend on
`atlas.ingestion` being installed or active (plugin-lifecycle spec) — this
module is imported by every other plugin's read/write views
(`api/helpers.py` module docstring), so a crash here would take all of them
down whenever ingestion is deselected."""

import pytest

from server.apps.catalog.api import helpers
from server.apps.catalog.models import CatalogEntity

pytestmark = pytest.mark.django_db


def test_blocked_by_returns_none_when_ingestion_is_not_installed(monkeypatch):
    monkeypatch.setattr(helpers.django_apps, "is_installed", lambda name: False)
    fake = CatalogEntity(kind="system", namespace="default", name="whatever")

    assert helpers.blocked_by(fake) is None


def test_blocked_by_returns_none_when_ingestion_is_disabled(monkeypatch):
    monkeypatch.setattr(
        "server.settings.selected_plugins.DISABLED_PLUGINS",
        frozenset({"atlas.ingestion"}),
    )
    fake = CatalogEntity(kind="system", namespace="default", name="whatever")

    assert helpers.blocked_by(fake) is None


def test_blocked_by_reason_returns_none_when_ingestion_is_not_installed(
    monkeypatch,
):
    monkeypatch.setattr(helpers.django_apps, "is_installed", lambda name: False)
    fake = CatalogEntity(kind="system", namespace="default", name="whatever")

    assert helpers.blocked_by_reason(fake) is None


def test_blocked_by_reason_returns_none_when_ingestion_is_disabled(monkeypatch):
    monkeypatch.setattr(
        "server.settings.selected_plugins.DISABLED_PLUGINS",
        frozenset({"atlas.ingestion"}),
    )
    fake = CatalogEntity(kind="system", namespace="default", name="whatever")

    assert helpers.blocked_by_reason(fake) is None


def test_resolve_adopt_repository_raises_cleanly_when_ingestion_not_installed(
    monkeypatch,
):
    monkeypatch.setattr(helpers.django_apps, "is_installed", lambda name: False)

    with pytest.raises(Exception) as exc_info:  # noqa: PT011 - dmr.response.APIError
        helpers.resolve_adopt_repository("someorg/somerepo")

    assert "not active" in str(exc_info.value.raw_data)


def test_resolve_adopt_repository_raises_cleanly_when_ingestion_is_disabled(
    monkeypatch,
):
    monkeypatch.setattr(
        "server.settings.selected_plugins.DISABLED_PLUGINS",
        frozenset({"atlas.ingestion"}),
    )

    with pytest.raises(Exception) as exc_info:  # noqa: PT011 - dmr.response.APIError
        helpers.resolve_adopt_repository("someorg/somerepo")

    assert "not active" in str(exc_info.value.raw_data)
