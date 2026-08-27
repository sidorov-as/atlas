from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

import pytest
from atlas_plugin_api import (
    AssuredAttribute,
    AttributeProvenance,
    ExternalGroupSnapshot,
    ExternalProfile,
    VerifiedIdentity,
)
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import close_old_connections, connections
from django.utils import timezone

from server.apps.catalog.membership import add_manual_membership
from server.apps.catalog.models import (
    AccountAccess,
    AuthenticationSecurityEvent,
    AuthenticationSourceBinding,
    ExternalIdentityLink,
    GroupMembershipGrant,
    ProvisioningAuditRecord,
)
from server.apps.catalog.provisioning import (
    EligibilityError,
    IdentityConflictError,
    ProvisioningError,
    StaleAuthenticationAttemptError,
    provision_verified_identity,
)

pytestmark = pytest.mark.django_db

PROVIDER = "example.auth.fixture"
SOURCE = "https://identity.example"


def _policy(**overrides):
    policy = {
        "id": PROVIDER,
        "principalProvisioning": "automatic",
        "actorProvisioning": "automatic",
        "profileFields": ("username", "displayName", "email"),
        "sourceBinding": {
            "sourceId": SOURCE,
            "configurationFingerprint": "sha256:fixture",
            "lockDigest": "sha256:lock",
        },
        "groupSync": {
            "mode": "exact",
            "snapshotRequirement": "required",
            "maxAgeSeconds": 28_800,
            "mappings": {"Engineering": "platform"},
        },
        "restrictedAttributes": (),
    }
    policy.update(overrides)
    return policy


def _identity(*, groups=("engineering",), username="alice", attributes=None):
    return VerifiedIdentity(
        provider_id=PROVIDER,
        source_id=SOURCE,
        subject="subject-42",
        profile=ExternalProfile(
            username=username,
            display_name="Alice Example",
            email="alice@example.com",
        ),
        attributes=attributes or {},
        groups=ExternalGroupSnapshot.complete(groups),
    )


def _provision(identity, policy, generation):
    return provision_verified_identity(
        identity,
        policy,
        correlation_id=f"correlation-{generation}",
        attempt_generation=generation,
    )


def test_automatic_pipeline_is_stable_and_reconciles_exact_grants(group):
    first = _provision(
        _identity(groups=("engineering", "unknown")), _policy(), 1
    )
    second = _provision(_identity(groups=(), username="renamed"), _policy(), 2)

    assert first.user.pk == second.user.pk
    assert ExternalIdentityLink.objects.count() == 1
    assert first.user.catalog_actor.entity_id == second.actor_id
    second.user.refresh_from_db()
    assert second.user.username == "renamed"
    assert second.user.email == "alice@example.com"
    assert not GroupMembershipGrant.objects.filter(
        identity_link=second.identity_link
    ).exists()
    assert ProvisioningAuditRecord.objects.filter(
        action="principal_created"
    ).exists()
    assert ProvisioningAuditRecord.objects.filter(
        action="actor_created"
    ).exists()
    binding = AuthenticationSourceBinding.objects.get()
    assert binding.configuration_fingerprint == "sha256:fixture"
    assert binding.lock_digest == "sha256:lock"


def test_none_and_additive_modes_have_distinct_reconciliation(group):
    none = _policy(
        actorProvisioning="manual",
        groupSync={"mode": "none"},
    )
    result = _provision(_identity(), none, 1)
    assert not GroupMembershipGrant.objects.filter(
        identity_link=result.identity_link
    ).exists()

    additive = _policy(
        groupSync={
            "mode": "additive",
            "snapshotRequirement": "best-effort",
            "mappings": {"engineering": "platform"},
        }
    )
    _provision(_identity(), additive, 2)
    _provision(_identity(groups=()), additive, 3)
    grant = GroupMembershipGrant.objects.get(identity_link=result.identity_link)
    assert grant.expires_at is None


def test_automatic_actor_for_existing_principal_does_not_claim_similar_actor(
    owner_account, other_user, group
):
    other_user.name = "alice"
    other_user.save(update_fields=("name",))
    link = ExternalIdentityLink.objects.create(
        user=owner_account,
        provider_id=PROVIDER,
        source_id=SOURCE,
        external_subject="subject-42",
    )

    result = _provision(_identity(), _policy(), 1)

    assert result.identity_link.pk == link.pk
    actor = owner_account.catalog_actor.entity
    assert actor.pk != other_user.pk
    assert actor.name.startswith("alice-")


def test_exact_removes_only_own_grant_and_keeps_manual_access(group):
    result = _provision(_identity(), _policy(), 1)
    actor = result.user.catalog_actor.entity
    add_manual_membership(group=group.group_details, actor=actor)

    _provision(_identity(groups=()), _policy(), 2)

    assert GroupMembershipGrant.objects.filter(
        actor=actor, source_kind=GroupMembershipGrant.SOURCE_MANUAL
    ).exists()
    assert not GroupMembershipGrant.objects.filter(
        actor=actor, identity_link=result.identity_link
    ).exists()


def test_incomplete_exact_snapshot_rolls_back_and_failure_event_survives(group):
    result = _provision(_identity(), _policy(), 1)
    unavailable = _identity(groups=())
    unavailable = VerifiedIdentity(
        provider_id=unavailable.provider_id,
        source_id=unavailable.source_id,
        subject=unavailable.subject,
        profile=unavailable.profile,
        groups=ExternalGroupSnapshot.unavailable(),
    )

    with pytest.raises(ProvisioningError, match="complete group snapshot"):
        _provision(unavailable, _policy(), 2)

    assert (
        GroupMembershipGrant.objects.filter(
            identity_link=result.identity_link
        ).count()
        == 1
    )
    assert AuthenticationSecurityEvent.objects.filter(
        category="provisioning_failed",
        correlation_id="correlation-2",
    ).exists()


def test_preprovisioned_absence_creates_no_partial_state():
    with pytest.raises(ProvisioningError, match="not preprovisioned"):
        _provision(
            _identity(groups=()),
            _policy(
                principalProvisioning="preprovisioned",
                actorProvisioning="manual",
                groupSync={"mode": "none"},
            ),
            1,
        )

    assert not get_user_model().objects.exists()
    assert not ExternalIdentityLink.objects.exists()
    assert AuthenticationSecurityEvent.objects.count() == 1


def test_profile_collision_never_auto_links_existing_principal(owner_account):
    owner_account.username = "alice"
    owner_account.save(update_fields=("username",))

    with pytest.raises(IdentityConflictError, match="username collides"):
        _provision(
            _identity(groups=()),
            _policy(actorProvisioning="manual", groupSync={"mode": "none"}),
            1,
        )

    assert not ExternalIdentityLink.objects.exists()
    assert get_user_model().objects.count() == 1


def test_restricted_policy_rechecks_existing_link_and_preserves_security_fields(
    group,
):
    requirement = (
        {
            "name": "email",
            "acceptedProvenance": ("verified-ownership",),
            "allowedDomains": ("example.com",),
        },
    )
    eligible = _identity(
        attributes={
            "email": AssuredAttribute(
                "alice@example.com", AttributeProvenance.VERIFIED_OWNERSHIP
            )
        }
    )
    policy = _policy(
        principalProvisioning="restricted",
        restrictedAttributes=requirement,
    )
    result = _provision(eligible, policy, 1)
    user = result.user
    user.is_staff = True
    user.save(update_fields=("is_staff",))
    access = AccountAccess.objects.create(account=user, read_only=True)
    password = user.password

    ineligible = _identity(
        attributes={
            "email": AssuredAttribute(
                "alice@evil.example", AttributeProvenance.VERIFIED_OWNERSHIP
            )
        }
    )
    with pytest.raises(EligibilityError):
        _provision(ineligible, policy, 2)

    result.identity_link.refresh_from_db()
    user.refresh_from_db()
    access.refresh_from_db()
    assert result.identity_link.revoked_at is not None
    assert user.is_staff is True
    assert user.password == password
    assert access.read_only is True


def test_repeated_and_second_provider_provisioning_preserve_read_only(
    owner_account,
    owner_user,
    group,
):
    """Authentication data and effective grants never own AccountAccess."""

    access = AccountAccess.objects.create(account=owner_account, read_only=True)
    first_link = ExternalIdentityLink.objects.create(
        user=owner_account,
        provider_id=PROVIDER,
        source_id=SOURCE,
        external_subject="subject-42",
    )
    role_like_attributes = {
        "role": AssuredAttribute(
            "administrator", AttributeProvenance.AUTHORITY_MANAGED
        )
    }

    first = _provision(
        _identity(attributes=role_like_attributes),
        _policy(),
        1,
    )
    add_manual_membership(group=group.group_details, actor=owner_user)
    second = _provision(
        _identity(username="renamed", attributes=role_like_attributes),
        _policy(),
        2,
    )

    second_provider = "example.auth.second"
    second_source = "https://identity-two.example"
    second_subject = "second-subject"
    second_link = ExternalIdentityLink.objects.create(
        user=owner_account,
        provider_id=second_provider,
        source_id=second_source,
        external_subject=second_subject,
    )
    second_identity = VerifiedIdentity(
        provider_id=second_provider,
        source_id=second_source,
        subject=second_subject,
        profile=_identity().profile,
        attributes=role_like_attributes,
        groups=ExternalGroupSnapshot.complete(("engineering",)),
    )
    second_policy = deepcopy(_policy())
    second_policy.update(
        {
            "id": second_provider,
            "principalProvisioning": "preprovisioned",
            "sourceBinding": {
                "sourceId": second_source,
                "configurationFingerprint": "sha256:second",
                "lockDigest": "sha256:second-lock",
            },
        }
    )
    third = _provision(second_identity, second_policy, 3)

    access.refresh_from_db()
    owner_account.refresh_from_db()
    assert access.read_only is True
    assert AccountAccess.objects.get(account=owner_account).pk == access.pk
    assert first.identity_link.pk == first_link.pk
    assert second.identity_link.pk == first_link.pk
    assert third.identity_link.pk == second_link.pk
    assert owner_account.is_staff is False
    assert owner_account.is_superuser is False
    assert GroupMembershipGrant.objects.filter(
        actor=owner_user,
        source_kind=GroupMembershipGrant.SOURCE_MANUAL,
    ).exists()
    assert (
        GroupMembershipGrant.objects.filter(
            actor=owner_user,
            source_kind=GroupMembershipGrant.SOURCE_PROVIDER,
            identity_link__in=(first_link, second_link),
        ).count()
        == 2
    )


def test_restricted_policy_rejects_unverified_email_without_creating_state():
    policy = _policy(
        principalProvisioning="restricted",
        restrictedAttributes=(
            {
                "name": "email",
                "acceptedProvenance": ("verified-ownership",),
                "allowedDomains": ("example.com",),
            },
        ),
    )
    identity = _identity(
        attributes={
            "email": AssuredAttribute(
                "alice@example.com",
                AttributeProvenance.SELF_ASSERTED,
            )
        }
    )

    with pytest.raises(EligibilityError):
        _provision(identity, policy, 1)

    assert not ExternalIdentityLink.objects.exists()
    assert not get_user_model().objects.exists()


def test_profile_policy_rejects_security_fields_without_mutation(group):
    policy = _policy(profileFields=("username", "read_only"))
    with pytest.raises(ProvisioningError, match="protected fields"):
        _provision(_identity(), policy, 1)
    assert not get_user_model().objects.exists()


def test_stale_attempt_cannot_overwrite_newer_snapshot(group):
    result = _provision(_identity(), _policy(), 10)
    with pytest.raises(StaleAuthenticationAttemptError):
        _provision(_identity(groups=()), _policy(), 9)
    assert (
        GroupMembershipGrant.objects.filter(
            identity_link=result.identity_link
        ).count()
        == 1
    )


def test_source_fingerprint_change_requires_reviewed_migration(group):
    _provision(_identity(), _policy(), 1)
    changed = deepcopy(_policy())
    changed["sourceBinding"]["configurationFingerprint"] = "sha256:changed"
    with pytest.raises(IdentityConflictError, match="authority changed"):
        _provision(_identity(), changed, 2)


def test_legacy_oidc_link_without_verified_source_blocks_automatic_login(
    owner_account,
):
    link = ExternalIdentityLink.objects.create(
        user=owner_account,
        provider_id=PROVIDER,
        source_id="",
        external_subject="subject-42",
    )

    with pytest.raises(IdentityConflictError, match="no verified source"):
        _provision(
            _identity(groups=()),
            _policy(actorProvisioning="manual", groupSync={"mode": "none"}),
            1,
        )

    assert ExternalIdentityLink.objects.get().pk == link.pk
    assert get_user_model().objects.count() == 1


def test_revoked_link_is_not_automatically_recreated(owner_account):
    link = ExternalIdentityLink.objects.create(
        user=owner_account,
        provider_id=PROVIDER,
        source_id=SOURCE,
        external_subject="subject-42",
        revoked_at=timezone.now(),
        revocation_generation=1,
    )
    with pytest.raises(IdentityConflictError, match="revoked"):
        _provision(
            _identity(groups=()),
            _policy(actorProvisioning="manual", groupSync={"mode": "none"}),
            1,
        )
    assert ExternalIdentityLink.objects.get().pk == link.pk


def test_identity_command_is_dry_run_audited_and_does_not_restore_grants(
    owner_account, group, capsys
):
    common = (
        "--provider",
        PROVIDER,
        "--source",
        SOURCE,
        "--subject",
        "subject-42",
        "--reason",
        "operator-reviewed",
    )
    call_command(
        "manage_auth_identity",
        "link",
        *common,
        "--principal-id",
        str(owner_account.pk),
    )
    assert not ExternalIdentityLink.objects.exists()
    call_command(
        "manage_auth_identity",
        "link",
        *common,
        "--principal-id",
        str(owner_account.pk),
        "--apply",
    )
    link = ExternalIdentityLink.objects.get()
    call_command("manage_auth_identity", "revoke", *common, "--apply")
    link.refresh_from_db()
    assert link.revoked_at is not None
    call_command("manage_auth_identity", "restore", *common, "--apply")
    link.refresh_from_db()
    assert link.revoked_at is None
    assert link.revocation_generation == 2
    assert ProvisioningAuditRecord.objects.filter(
        action="identity_restore", identity_link_id=link.pk
    ).exists()
    call_command(
        "manage_auth_identity",
        "inspect",
        "--provider",
        PROVIDER,
        "--source",
        SOURCE,
    )
    assert "subject=subject-42" in capsys.readouterr().out


def test_identity_command_migrates_source_binding_generation(owner_account):
    link = ExternalIdentityLink.objects.create(
        user=owner_account,
        provider_id=PROVIDER,
        source_id=SOURCE,
        external_subject="subject-42",
    )
    old = AuthenticationSourceBinding.objects.create(
        provider_id=PROVIDER,
        source_id=SOURCE,
        configuration_fingerprint="sha256:fixture",
        lock_digest="sha256:lock",
    )
    call_command(
        "manage_auth_identity",
        "source-migrate",
        "--provider",
        PROVIDER,
        "--source",
        SOURCE,
        "--subject",
        "subject-42",
        "--to-source",
        "https://new-identity.example",
        "--reason",
        "issuer replacement reviewed",
        "--apply",
    )
    link.refresh_from_db()
    old.refresh_from_db()
    new = AuthenticationSourceBinding.objects.get(
        source_id="https://new-identity.example"
    )
    assert link.source_id == new.source_id
    assert old.revoked_at is not None
    assert new.generation == 2


@pytest.mark.django_db(transaction=True)
def test_concurrent_first_login_creates_one_identity_and_actor():
    from atlas_plugin_standard_catalog.models import GroupDetails

    from server.apps.catalog.models import KIND_GROUP, CatalogEntity

    group = CatalogEntity.objects.create(kind=KIND_GROUP, name="platform")
    GroupDetails.objects.create(entity=group, type="team")

    def run(generation):
        close_old_connections()
        try:
            return _provision(_identity(), _policy(), generation)
        except StaleAuthenticationAttemptError:
            return None
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(run, (1, 2)))

    assert any(result is not None for result in results)
    assert get_user_model().objects.count() == 1
    assert ExternalIdentityLink.objects.count() == 1
    assert get_user_model().objects.get().catalog_actor is not None


def test_privileged_link_requires_explicit_option(superuser_account):
    with pytest.raises(Exception, match="privileged-target"):
        call_command(
            "manage_auth_identity",
            "link",
            "--provider",
            PROVIDER,
            "--source",
            SOURCE,
            "--subject",
            "admin-subject",
            "--principal-id",
            str(superuser_account.pk),
            "--reason",
            "reviewed",
            "--apply",
        )
