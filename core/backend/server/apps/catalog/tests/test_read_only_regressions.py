"""Backend regression coverage for the account-wide read-only restriction."""

import json

import pytest
from atlas_plugin_ingestion.models import RegisteredRepository
from django.test import Client

from server.apps.catalog.authorization import has_purge_grant
from server.apps.catalog.models import (
    AccountAccess,
    ArchitectureRelationship,
    CatalogEntity,
    CatalogHomeSettings,
    EntityAuditRecord,
    PurgeGrant,
    Tag,
)

pytestmark = pytest.mark.django_db


def _relationship_payload(source, target):
    return {
        "source": source.ref,
        "target": target.ref,
        "label": "Calls",
        "interactionKind": "synchronous",
    }


def test_read_only_owner_member_cannot_mutate_entities_or_relationships(
    owner_client,
    owner_account,
    owner_user,
    group,
    system,
    component,
    api,
):
    AccountAccess.objects.create(account=owner_account, read_only=True)
    repository = RegisteredRepository.objects.create(
        source_id="test-source",
        path="org/repo",
    )
    relationship = ArchitectureRelationship.objects.create(
        source=component,
        target=api,
        label="Original",
    )
    original_audit_count = EntityAuditRecord.objects.count()

    create = owner_client.post(
        "/api/systems/",
        {"metadata": {"name": "blocked"}, "spec": {"owner": group.ref}},
    )
    edit = owner_client.patch(
        f"/api/systems/{system.id}/",
        {"metadata": {"title": "Blocked"}},
    )
    remove = owner_client.post(f"/api/systems/{system.id}/remove/")
    adopt = owner_client.post(
        f"/api/systems/{system.id}/adopt/",
        {"repository": str(repository)},
    )
    create_relationship = owner_client.post(
        "/api/architecture-relationships/",
        _relationship_payload(component, api),
    )
    edit_relationship = owner_client.patch(
        f"/api/architecture-relationships/{relationship.id}/",
        {"label": "Blocked"},
    )
    delete_relationship = owner_client.delete(
        f"/api/architecture-relationships/{relationship.id}/",
    )

    system.status = CatalogEntity.STATUS_REMOVED
    system.save(update_fields=["status"])
    revive = owner_client.post(f"/api/systems/{system.id}/revive/")
    PurgeGrant.objects.create(group=group, grantee=owner_account)
    purge = owner_client.post(f"/api/systems/{system.id}/purge/")

    assert {
        create.status_code,
        edit.status_code,
        remove.status_code,
        adopt.status_code,
        create_relationship.status_code,
        edit_relationship.status_code,
        delete_relationship.status_code,
        revive.status_code,
        purge.status_code,
    } == {403}
    assert not CatalogEntity.objects.filter(name="blocked").exists()
    system.refresh_from_db()
    assert system.title == ""
    assert system.status == CatalogEntity.STATUS_REMOVED
    assert system.source_kind == CatalogEntity.SOURCE_MANUAL
    relationship.refresh_from_db()
    assert relationship.label == "Original"
    assert ArchitectureRelationship.objects.count() == 1
    assert EntityAuditRecord.objects.count() == original_audit_count
    assert group.group_details.members.filter(pk=owner_user.pk).exists()
    assert PurgeGrant.objects.filter(
        group=group,
        grantee=owner_account,
    ).exists()


def test_read_only_superuser_cannot_use_direct_privilege_mutations(
    superuser_client,
    superuser_account,
    group,
    system,
):
    AccountAccess.objects.create(account=superuser_account, read_only=True)
    grant = PurgeGrant.objects.create(group=group, grantee=superuser_account)
    tag = Tag.objects.create(name="security")
    original_home = CatalogHomeSettings.get_solo().about_markdown

    tag_response = superuser_client.patch(
        f"/api/tags/{tag.id}/",
        {"color": "blue"},
    )
    home_response = superuser_client.patch(
        "/api/catalog-home-settings/",
        {"aboutMarkdown": "Blocked"},
    )
    create_response = superuser_client.post(
        "/api/systems/",
        {"metadata": {"name": "admin-blocked"}, "spec": {"owner": group.ref}},
    )
    edit_response = superuser_client.patch(
        f"/api/systems/{system.id}/",
        {"metadata": {"title": "Blocked"}},
    )
    remove_response = superuser_client.post(
        f"/api/systems/{system.id}/remove/",
    )

    assert tag_response.status_code == 403
    assert home_response.status_code == 403
    assert create_response.status_code == 403
    assert edit_response.status_code == 403
    assert remove_response.status_code == 403
    tag.refresh_from_db()
    assert tag.color != "blue"
    assert CatalogHomeSettings.get_solo().about_markdown == original_home
    system.refresh_from_db()
    assert system.title == ""
    assert system.status == CatalogEntity.STATUS_ACTIVE
    assert not CatalogEntity.objects.filter(name="admin-blocked").exists()
    assert has_purge_grant(superuser_account, group) is False
    assert PurgeGrant.objects.filter(pk=grant.pk).exists()


def test_existing_sessions_observe_flag_changes_without_reauthentication(
    owner_account,
    owner_user,
    system,
):
    first_session = Client()
    second_session = Client()
    first_session.force_login(owner_account)
    second_session.force_login(owner_account)

    assert (
        first_session.patch(
            f"/api/systems/{system.id}/",
            data=json.dumps({"metadata": {"title": "Before"}}),
            content_type="application/json",
        ).status_code
        == 200
    )

    access = AccountAccess.objects.create(account=owner_account, read_only=True)
    for session in (first_session, second_session):
        response = session.patch(
            f"/api/systems/{system.id}/",
            data=json.dumps({"metadata": {"title": "Blocked"}}),
            content_type="application/json",
        )
        assert response.status_code == 403

    access.read_only = False
    access.save(update_fields=["read_only", "updated_at"])
    assert (
        second_session.patch(
            f"/api/systems/{system.id}/",
            data=json.dumps({"metadata": {"title": "After"}}),
            content_type="application/json",
        ).status_code
        == 200
    )
    system.refresh_from_db()
    assert system.title == "After"
    assert system.owner.group_details.members.filter(pk=owner_user.pk).exists()


def test_read_only_user_can_read_login_logout_and_cannot_claim_service_source(
    owner_account,
    owner_user,
    system,
):
    AccountAccess.objects.create(account=owner_account, read_only=True)
    client = Client()

    login = client.post(
        "/_allauth/browser/v1/auth/login",
        data=json.dumps(
            {
                "username": owner_account.username,
                "password": "password123",
            }
        ),
        content_type="application/json",
    )
    assert login.status_code == 200
    assert client.get(f"/api/systems/{system.id}/").status_code == 200
    response = client.post(
        "/api/systems/",
        data=json.dumps(
            {
                "metadata": {"name": "source-bypass"},
                "spec": {"owner": system.owner.ref},
                "source": "ingestion",
            }
        ),
        content_type="application/json",
    )
    assert response.status_code == 403
    assert not CatalogEntity.objects.filter(name="source-bypass").exists()
    logout = client.delete("/_allauth/browser/v1/auth/session")
    assert logout.status_code == 401
    assert client.get("/api/me/").status_code == 401
    assert AccountAccess.objects.get(account=owner_account).read_only is True
    assert system.owner.group_details.members.filter(pk=owner_user.pk).exists()
