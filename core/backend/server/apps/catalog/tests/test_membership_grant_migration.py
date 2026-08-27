from datetime import timedelta

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone


@pytest.mark.django_db(transaction=True)
def test_membership_grant_forward_and_reverse_migration_preserves_pairs():
    executor = MigrationExecutor(connection)
    executor.migrate([("catalog", "0026_authenticationattempt")])
    old_apps = executor.loader.project_state(
        [("catalog", "0026_authenticationattempt")]
    ).apps
    CatalogEntity = old_apps.get_model("catalog", "CatalogEntity")
    GroupDetails = old_apps.get_model("catalog", "GroupDetails")
    User = old_apps.get_model("auth", "User")
    AccountAccess = old_apps.get_model("catalog", "AccountAccess")
    AccountAccessAuditRecord = old_apps.get_model(
        "catalog", "AccountAccessAuditRecord"
    )
    account = User.objects.create(username="legacy-principal")
    access = AccountAccess.objects.create(account=account, read_only=True)
    access_audit = AccountAccessAuditRecord.objects.create(
        target_id=account.pk,
        target_username=account.username,
        action="create",
        old_read_only=None,
        new_read_only=True,
        reason="migration preservation fixture",
    )
    group_entity = CatalogEntity.objects.create(
        kind="group", name="legacy-team"
    )
    actor = CatalogEntity.objects.create(kind="user", name="legacy-actor")
    group = GroupDetails.objects.create(entity=group_entity, type="team")
    group.members.add(actor)

    executor = MigrationExecutor(connection)
    executor.migrate([("catalog", "0027_group_membership_grants")])
    new_apps = executor.loader.project_state(
        [("catalog", "0027_group_membership_grants")]
    ).apps
    Grant = new_apps.get_model("catalog", "GroupMembershipGrant")
    migrated = Grant.objects.get(group_id=group_entity.pk, actor_id=actor.pk)
    assert migrated.source_kind == "manual"
    assert migrated.legacy_unclassified is True
    ForwardAccess = new_apps.get_model("catalog", "AccountAccess")
    ForwardAudit = new_apps.get_model("catalog", "AccountAccessAuditRecord")
    assert ForwardAccess.objects.get(pk=access.pk).read_only is True
    assert ForwardAudit.objects.get(pk=access_audit.pk).new_read_only is True

    # Rollback collapses multiple independent grants to one legacy pair and
    # intentionally loses provenance, while preserving effective access.
    Link = new_apps.get_model("catalog", "ExternalIdentityLink")
    link = Link.objects.create(
        user_id=account.pk,
        provider_id="atlas.auth.oidc",
        source_id="https://idp.example.com",
        external_subject="legacy-subject",
    )
    Grant.objects.create(
        group_id=group_entity.pk,
        actor_id=actor.pk,
        source_kind="provider",
        identity_link=link,
        external_key="engineering",
        expires_at=timezone.now() + timedelta(hours=8),
        last_confirmed_at=timezone.now(),
    )
    expired_actor = CatalogEntity.objects.create(
        kind="user", name="expired-provider-actor"
    )
    Grant.objects.create(
        group_id=group_entity.pk,
        actor_id=expired_actor.pk,
        source_kind="provider",
        identity_link=link,
        external_key="expired-engineering",
        expires_at=timezone.now() - timedelta(seconds=1),
        last_confirmed_at=timezone.now() - timedelta(hours=9),
    )
    revoked_actor = CatalogEntity.objects.create(
        kind="user", name="revoked-provider-actor"
    )
    Grant.objects.create(
        group_id=group_entity.pk,
        actor_id=revoked_actor.pk,
        source_kind="provider",
        identity_link=link,
        external_key="revoked-engineering",
        expires_at=timezone.now() + timedelta(hours=8),
        revoked_at=timezone.now(),
        last_confirmed_at=timezone.now(),
    )

    executor = MigrationExecutor(connection)
    executor.migrate([("catalog", "0026_authenticationattempt")])
    rolled_back_apps = executor.loader.project_state(
        [("catalog", "0026_authenticationattempt")]
    ).apps
    RolledBackGroup = rolled_back_apps.get_model("catalog", "GroupDetails")
    restored = RolledBackGroup.objects.get(pk=group_entity.pk)
    assert list(restored.members.values_list("pk", flat=True)) == [actor.pk]
    RolledBackAccess = rolled_back_apps.get_model("catalog", "AccountAccess")
    RolledBackAudit = rolled_back_apps.get_model(
        "catalog", "AccountAccessAuditRecord"
    )
    assert RolledBackAccess.objects.get(pk=access.pk).read_only is True
    assert (
        RolledBackAudit.objects.get(pk=access_audit.pk).reason
        == "migration preservation fixture"
    )

    # Expired and revoked provider grants are deliberately not resurrected.
    assert not restored.members.filter(pk=expired_actor.pk).exists()
    assert not restored.members.filter(pk=revoked_actor.pk).exists()

    # Leave the shared test database at the repository's latest schema.
    MigrationExecutor(connection).migrate(
        [("catalog", "0029_authentication_security")]
    )
