import pytest
from django.conf import settings

from server.health import AtlasHealthCheckView


@pytest.mark.django_db
def test_healthz_and_security_headers(client):
    response = client.get("/healthz/")

    assert response.status_code == 200
    assert "Content-Security-Policy" in response.headers


def test_healthz_does_not_check_filesystem_storage():
    assert "health_check.checks.Storage" not in AtlasHealthCheckView.checks


def test_spa_origins_are_explicit():
    assert "http://localhost:5173" in settings.CSRF_TRUSTED_ORIGINS
    assert "http://localhost:5173" in settings.CORS_ALLOWED_ORIGINS


def test_csrf_cookie_is_readable_by_the_spa():
    assert settings.CSRF_COOKIE_HTTPONLY is False
    assert settings.SESSION_COOKIE_HTTPONLY is True
    assert settings.CSRF_COOKIE_SAMESITE == "Lax"
    assert settings.SESSION_COOKIE_SAMESITE == "Lax"
