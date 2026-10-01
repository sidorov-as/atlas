"""Django-admin issuance and revocation of Personal Access Tokens."""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from server.apps.catalog.models import PersonalAccessToken
from server.apps.catalog.services.pat_service import (
    issue_personal_access_token,
    validate_personal_access_token,
)

pytestmark = pytest.mark.django_db

User = get_user_model()


@pytest.fixture
def admin_client():
    admin_user = User.objects.create_superuser("root", "root@example.com", "pw")
    client = Client()
    client.force_login(admin_user)
    return client, admin_user


def test_add_redirects_to_the_issue_form(admin_client):
    client, _ = admin_client

    response = client.get(reverse("admin:catalog_personalaccesstoken_add"))

    assert response.status_code == 302
    assert response.url == reverse("admin:catalog_personalaccesstoken_issue")


def test_issue_shows_a_working_plaintext_token_once(admin_client):
    client, admin_user = admin_client

    response = client.post(
        reverse("admin:catalog_personalaccesstoken_issue"),
        {
            "owner": admin_user.pk,
            "name": "claude",
            "scopes": ["catalog:read", "catalog:write"],
            "expires_in_days": 30,
        },
    )

    assert response.status_code == 200
    plaintext = response.context["issued"].plaintext
    assert plaintext in response.content.decode()
    token = PersonalAccessToken.objects.get()
    assert token.name == "claude"
    assert token.scopes == ["catalog:read", "catalog:write"]
    assert token.expires_at is not None
    resolved = validate_personal_access_token(plaintext)
    assert resolved is not None and resolved.user == admin_user
    assert "no-store" in response["Cache-Control"]


def test_issue_requires_add_permission():
    staff = User.objects.create_user("staff", password="pw", is_staff=True)
    client = Client()
    client.force_login(staff)

    response = client.post(
        reverse("admin:catalog_personalaccesstoken_issue"), {"owner": staff.pk}
    )

    assert response.status_code == 403
    assert not PersonalAccessToken.objects.exists()


def test_revoke_action_revokes_selected_tokens_and_keeps_existing_revocation(
    admin_client,
):
    client, admin_user = admin_client
    first = issue_personal_access_token(owner=admin_user)
    second = issue_personal_access_token(owner=admin_user)

    response = client.post(
        reverse("admin:catalog_personalaccesstoken_changelist"),
        {
            "action": "revoke_tokens",
            "_selected_action": [first.instance.pk],
        },
    )

    assert response.status_code == 302
    assert validate_personal_access_token(first.plaintext) is None
    assert validate_personal_access_token(second.plaintext) is not None
