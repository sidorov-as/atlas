"""Django-admin and recovery regressions for read-only account state."""

from io import StringIO
from unittest.mock import patch

import pytest
from atlas_plugin_apis.models import ApiEndpoint
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.db import transaction
from django.test import Client, RequestFactory

from server.apps.catalog.admin import AccountAccessInline, UserAdmin
from server.apps.catalog.models import (
    AccountAccess,
    AccountAccessAuditRecord,
    CatalogEntity,
)

pytestmark = pytest.mark.django_db

User = get_user_model()


class _AccountAccessFormset:
    model = AccountAccess

    def __init__(self, instance):
        self.instance = instance

    def save(self, commit=False):
        assert commit is False
        return [self.instance]

    def save_m2m(self):
        return None


def _request(user):
    request = RequestFactory().post("/admin/auth/user/")
    request.user = user
    return request


def _user_add_payload(username):
    return {
        "username": username,
        "usable_password": "true",
        "password1": "safe-password-123",  # noqa: S106
        "password2": "safe-password-123",  # noqa: S106
        "account_access-TOTAL_FORMS": "1",
        "account_access-INITIAL_FORMS": "0",
        "account_access-MIN_NUM_FORMS": "0",
        "account_access-MAX_NUM_FORMS": "1",
        "account_access-0-read_only": "on",
        "_save": "Save",
    }


def test_read_only_superuser_cannot_craft_inline_bulk_or_custom_admin_writes(
    superuser_client,
    superuser_account,
    system,
):
    access = AccountAccess.objects.create(
        account=superuser_account,
        read_only=True,
    )

    view = superuser_client.get(
        f"/admin/auth/user/{superuser_account.pk}/change/",
    )
    crafted_inline = superuser_client.post(
        f"/admin/auth/user/{superuser_account.pk}/change/",
        {
            "username": superuser_account.username,
            "account_access-TOTAL_FORMS": "1",
            "account_access-INITIAL_FORMS": "1",
            "account_access-0-id": str(access.pk),
            "account_access-0-account": str(superuser_account.pk),
        },
    )
    add = superuser_client.post(
        "/admin/catalog/catalogentity/add/",
        {"name": "blocked"},
    )
    bulk = superuser_client.post(
        "/admin/catalog/catalogentity/",
        {
            "action": "delete_selected",
            "_selected_action": [str(system.pk)],
            "index": "0",
        },
    )

    request = _request(superuser_account)
    api_endpoint_admin = admin.site._registry[ApiEndpoint]

    assert view.status_code == 200
    assert crafted_inline.status_code == 403
    assert add.status_code == 403
    assert bulk.status_code == 200
    assert api_endpoint_admin.get_actions(request) == {}
    access.refresh_from_db()
    assert access.read_only is True
    assert CatalogEntity.objects.filter(pk=system.pk).exists()
    assert AccountAccess not in admin.site._registry
    assert AccountAccessInline.can_delete is False


def test_inline_requires_explicit_account_access_permission(owner_account):
    owner_account.is_staff = True
    owner_account.user_permissions.add(
        Permission.objects.get(codename="change_user"),
    )
    inline = AccountAccessInline(User, admin.site)
    request = _request(owner_account)

    assert inline.has_change_permission(request) is False

    owner_account.user_permissions.add(
        Permission.objects.get(codename="change_accountaccess"),
    )
    owner_account = User.objects.get(pk=owner_account.pk)
    request.user = owner_account
    assert inline.has_change_permission(request) is True


def test_flag_write_and_audit_commit_together(
    superuser_account,
    owner_account,
):
    instance = AccountAccess(account=owner_account, read_only=True)
    formset = _AccountAccessFormset(instance)
    user_admin = UserAdmin(User, admin.site)

    with transaction.atomic():
        user_admin.save_formset(
            _request(superuser_account),
            None,
            formset,
            change=False,
        )

    access = AccountAccess.objects.get(account=owner_account)
    audit = AccountAccessAuditRecord.objects.get(target_id=owner_account.pk)
    assert access.read_only is True
    assert audit.operator == superuser_account
    assert audit.old_read_only is None
    assert audit.new_read_only is True
    assert audit.timestamp is not None


def test_admin_creates_flagged_user_and_audit_atomically(superuser_account):
    client = Client()
    client.force_login(superuser_account)
    response = client.post(
        "/admin/auth/user/add/",
        _user_add_payload("flagged-user"),
    )

    assert response.status_code == 302
    target = User.objects.get(username="flagged-user")
    assert AccountAccess.objects.get(account=target).read_only is True
    audit = AccountAccessAuditRecord.objects.get(target_id=target.pk)
    assert audit.old_read_only is None
    assert audit.new_read_only is True


def test_admin_user_creation_rolls_back_when_inline_audit_fails(
    superuser_account,
):
    client = Client()
    client.force_login(superuser_account)
    with (
        patch.object(
            AccountAccessAuditRecord.objects,
            "create",
            side_effect=RuntimeError("audit unavailable"),
        ),
        pytest.raises(RuntimeError),
    ):
        client.post(
            "/admin/auth/user/add/",
            _user_add_payload("rolled-back-user"),
        )

    assert not User.objects.filter(username="rolled-back-user").exists()
    assert not AccountAccess.objects.filter(
        account__username="rolled-back-user",
    ).exists()


def test_flag_write_rolls_back_when_audit_fails(
    superuser_account,
    owner_account,
):
    instance = AccountAccess(account=owner_account, read_only=True)
    formset = _AccountAccessFormset(instance)
    user_admin = UserAdmin(User, admin.site)

    with (
        pytest.raises(RuntimeError),
        patch.object(
            AccountAccessAuditRecord.objects,
            "create",
            side_effect=RuntimeError("audit unavailable"),
        ),
        transaction.atomic(),
    ):
        user_admin.save_formset(
            _request(superuser_account),
            None,
            formset,
            change=False,
        )

    assert not AccountAccess.objects.filter(account=owner_account).exists()
    assert not AccountAccessAuditRecord.objects.filter(
        target_id=owner_account.pk,
    ).exists()


def test_recovery_command_is_dry_run_by_default_and_audits_confirmed_change(
    owner_account,
):
    access = AccountAccess.objects.create(
        account=owner_account,
        read_only=True,
    )
    output = StringIO()

    call_command(
        "clear_read_only",
        owner_account.username,
        reason="operator lockout",
        stdout=output,
    )
    access.refresh_from_db()
    assert access.read_only is True
    assert "Dry run only" in output.getvalue()
    assert not AccountAccessAuditRecord.objects.exists()

    call_command(
        "clear_read_only",
        owner_account.username,
        reason="operator lockout",
        confirm=True,
        stdout=StringIO(),
    )
    access.refresh_from_db()
    audit = AccountAccessAuditRecord.objects.get(target_id=owner_account.pk)
    assert access.read_only is False
    assert audit.operator is None
    assert audit.old_read_only is True
    assert audit.new_read_only is False
    assert audit.reason == "[infrastructure recovery] operator lockout"
