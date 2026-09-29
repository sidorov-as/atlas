import logging

import pytest
from django.conf import settings
from health_check.checks import Database
from health_check.exceptions import ServiceUnavailable

from server.health import AtlasHealthCheckView


@pytest.mark.django_db
def test_healthz_and_security_headers(client):
    response = client.get("/healthz/")

    assert response.status_code == 200
    assert "Content-Security-Policy" in response.headers


@pytest.mark.django_db
def test_healthz_logs_each_failing_check(client, monkeypatch, caplog):
    def broken(self):
        raise ServiceUnavailable("boom")

    monkeypatch.setattr(Database, "run", broken)

    with caplog.at_level(logging.ERROR, logger="server.health"):
        response = client.get("/healthz/")

    assert response.status_code == 500
    assert "Health check failed" in caplog.text
    assert "Database" in caplog.text
    assert "boom" in caplog.text


def test_healthz_does_not_check_filesystem_storage():
    assert "health_check.checks.Storage" not in AtlasHealthCheckView.checks


def test_healthz_does_not_check_dns():
    assert "health_check.checks.DNS" not in AtlasHealthCheckView.checks
    assert "health_check.checks.Database" in AtlasHealthCheckView.checks


def test_spa_origins_are_explicit():
    assert "http://localhost:5173" in settings.CSRF_TRUSTED_ORIGINS
    assert "http://localhost:5173" in settings.CORS_ALLOWED_ORIGINS


def test_csrf_cookie_is_readable_by_the_spa():
    assert settings.CSRF_COOKIE_HTTPONLY is False
    assert settings.SESSION_COOKIE_HTTPONLY is True
    assert settings.CSRF_COOKIE_SAMESITE == "Lax"
    assert settings.SESSION_COOKIE_SAMESITE == "Lax"
