from datetime import timedelta

import pytest
from django.core.management import CommandError, call_command
from django.utils import timezone

from server.apps.catalog.authorization import is_group_member, policy_evaluator
from server.apps.catalog.membership import (
    add_manual_membership,
    add_provider_membership,
    effective_grants,
    ensure_exact_membership_ready,
    is_effective_member,
    remove_manual_membership,
    set_manual_memberships,
)
from server.apps.catalog.models import (
    KIND_CHOICES,
    CatalogEntity,
    ExternalIdentityLink,
    GroupMembershipGrant,
    MembershipGrantAuditRecord,
)

pytestmark = pytest.mark.django_db

SOURCE = "https://idp.example.com"


@pytest.fixture
def exact_policy(settings):
    settings.ATLAS_AUTHENTICATION = {
        "providers": (
            {
                "id": "atlas.auth.local",
                "sourceBinding": {"sourceId": "atlas.local"},
                "groupSync": {"mode": "none"},
            },
            {
                "id": "atlas.auth.oidc",
                "sourceBinding": {"sourceId": SOURCE},
                "groupSync": {"mode": "exact", "maxAgeSeconds": 28_800},
            },
        ),
        "default": "atlas.auth.local",
    }


def _link(account, subject):
    return ExternalIdentityLink.objects.create(
        user=account,
        provider_id="atlas.auth.oidc",
        source_id=SOURCE,
        external_subject=subject,
    )


def test_independent_manual_and_provider_grants_preserve_effective_access(
    owner_user, owner_account, group, exact_policy
):
    manual = GroupMembershipGrant.objects.get(
        group=group.group_details,
        actor=owner_user,
        source_kind="manual",
    )
    first = add_provider_membership(
        group=group.group_details,
        actor=owner_user,
        identity_link=_link(owner_account, "one"),
        external_key="engineering",
        expires_at=timezone.now() + timedelta(hours=8),
    )
    second = add_provider_membership(
        group=group.group_details,
        actor=owner_user,
        identity_link=_link(owner_account, "two"),
        external_key="engineering",
        expires_at=timezone.now() + timedelta(hours=8),
    )

    manual.delete()
    assert is_effective_member(actor=owner_user, group=group.group_details)
    first.delete()
    assert is_effective_member(actor=owner_user, group=group.group_details)
    second.delete()
    assert not is_effective_member(actor=owner_user, group=group.group_details)


def test_manual_replacement_never_removes_provider_grants(
    owner_user, owner_account, other_user, group, exact_policy
):
    provider = add_provider_membership(
        group=group.group_details,
        actor=owner_user,
        identity_link=_link(owner_account, "one"),
        external_key="engineering",
        expires_at=timezone.now() + timedelta(hours=8),
    )
    set_manual_memberships(group.group_details, [owner_user, other_user])
    set_manual_memberships(group.group_details, [other_user])

    assert GroupMembershipGrant.objects.filter(pk=provider.pk).exists()
    assert is_effective_member(actor=owner_user, group=group.group_details)
    assert (
        remove_manual_membership(group=group.group_details, actor=owner_user)
        is False
    )


def test_group_api_reports_effective_membership_and_each_source_grant(
    owner_client, owner_user, owner_account, group, exact_policy
):
    # The policy fixture deliberately changes authoritative auth selection;
    # establish this test session after that generation change.
    owner_client.force_login(owner_account)
    add_provider_membership(
        group=group.group_details,
        actor=owner_user,
        identity_link=_link(owner_account, "api-source"),
        external_key="engineering",
        expires_at=timezone.now() + timedelta(hours=8),
    )

    response = owner_client.get(f"/api/groups/{group.pk}/")

    assert response.status_code == 200
    membership = response.json()["spec"]["membershipGrants"][0]
    assert membership["entity"] == owner_user.ref
    assert membership["effective"] is True
    assert {grant["sourceKind"] for grant in membership["grants"]} == {
        "manual",
        "provider",
    }
    provider = next(
        grant
        for grant in membership["grants"]
        if grant["sourceKind"] == "provider"
    )
    assert provider["providerId"] == "atlas.auth.oidc"
    assert provider["sourceId"] == SOURCE
    assert provider["externalKey"] == "engineering"
    assert provider["applicable"] is True


def test_exact_expiry_and_independent_manual_grant(
    owner_client, owner_user, owner_account, group, system, exact_policy
):
    owner_client.force_login(owner_account)
    remove_manual_membership(group=group.group_details, actor=owner_user)
    grant = add_provider_membership(
        group=group.group_details,
        actor=owner_user,
        identity_link=_link(owner_account, "one"),
        external_key="engineering",
        expires_at=timezone.now() + timedelta(hours=8),
    )
    assert policy_evaluator.check(owner_account, "system.edit", system)
    assert (
        owner_client.patch(
            f"/api/systems/{system.pk}/", {"metadata": {"title": "fresh"}}
        ).status_code
        == 200
    )

    # Authorization is evaluated from the grant on every request. A still-live
    # Principal session (including one established by another provider) cannot
    # keep an expired exact grant effective, and no cleanup job is required.
    GroupMembershipGrant.objects.filter(pk=grant.pk).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )
    assert not effective_grants(
        actor=owner_user, group=group.group_details
    ).exists()
    assert not policy_evaluator.check(owner_account, "system.edit", system)
    assert (
        owner_client.patch(
            f"/api/systems/{system.pk}/", {"metadata": {"title": "expired"}}
        ).status_code
        == 403
    )

    add_manual_membership(group=group.group_details, actor=owner_user)
    assert is_effective_member(actor=owner_user, group=group.group_details)
    assert policy_evaluator.check(owner_account, "system.edit", system)
    assert (
        owner_client.patch(
            f"/api/systems/{system.pk}/", {"metadata": {"title": "manual"}}
        ).status_code
        == 200
    )


def test_shortened_freshness_and_provider_deselection_apply_to_existing_grants(
    settings, owner_user, owner_account, group, exact_policy
):
    remove_manual_membership(group=group.group_details, actor=owner_user)
    grant = add_provider_membership(
        group=group.group_details,
        actor=owner_user,
        identity_link=_link(owner_account, "one"),
        external_key="engineering",
        expires_at=timezone.now() + timedelta(hours=8),
    )
    GroupMembershipGrant.objects.filter(pk=grant.pk).update(
        last_confirmed_at=timezone.now() - timedelta(hours=2)
    )
    settings.ATLAS_AUTHENTICATION["providers"][1]["groupSync"][
        "maxAgeSeconds"
    ] = 60
    assert not is_effective_member(actor=owner_user, group=group.group_details)

    settings.ATLAS_AUTHENTICATION = {"providers": (), "default": None}
    assert not is_effective_member(actor=owner_user, group=group.group_details)


def test_revoked_source_link_is_not_effective(
    owner_user, owner_account, group, exact_policy
):
    remove_manual_membership(group=group.group_details, actor=owner_user)
    link = _link(owner_account, "one")
    add_provider_membership(
        group=group.group_details,
        actor=owner_user,
        identity_link=link,
        external_key="engineering",
        expires_at=timezone.now() + timedelta(hours=8),
    )
    link.revoked_at = timezone.now()
    link.save(update_fields=("revoked_at",))
    assert not is_group_member(owner_account, group)


def test_legacy_classification_command_is_dry_run_then_audited_apply(
    owner_user, group, capsys
):
    grant = GroupMembershipGrant.objects.get(
        group=group.group_details,
        actor=owner_user,
        source_kind="manual",
    )
    grant.legacy_unclassified = True
    grant.save(update_fields=("legacy_unclassified",))
    with pytest.raises(CommandError, match="1 legacy grant"):
        call_command("check_membership_grants")
    call_command(
        "classify_membership_grant",
        grant.pk,
        "--as-manual",
        "--reason",
        "reviewed",
    )
    grant.refresh_from_db()
    assert grant.legacy_unclassified is True

    call_command(
        "classify_membership_grant",
        grant.pk,
        "--as-manual",
        "--reason",
        "reviewed",
        "--apply",
    )
    grant.refresh_from_db()
    assert grant.legacy_unclassified is False
    assert MembershipGrantAuditRecord.objects.filter(grant_id=grant.pk).exists()
    call_command("check_membership_grants")


def test_legacy_oidc_grant_can_transfer_without_residual_manual_access(
    owner_user, owner_account, group, exact_policy
):
    grant = GroupMembershipGrant.objects.get(
        group=group.group_details, actor=owner_user, source_kind="manual"
    )
    grant.legacy_unclassified = True
    grant.save(update_fields=("legacy_unclassified",))
    link = _link(owner_account, "legacy-oidc")

    call_command(
        "classify_membership_grant",
        grant.pk,
        "--identity-link-id",
        link.pk,
        "--external-key",
        "engineering",
        "--reason",
        "historical OIDC ownership verified",
        "--apply",
    )
    grant.refresh_from_db()
    assert grant.source_kind == "provider"
    assert not GroupMembershipGrant.objects.filter(
        group=group.group_details, actor=owner_user, source_kind="manual"
    ).exists()

    # A later complete exact snapshot omitting this group removes the
    # transferred grant; no legacy manual duplicate keeps access alive.
    grant.delete()
    assert not is_effective_member(actor=owner_user, group=group.group_details)


def test_exact_activation_requires_classification_or_explicit_acknowledgement(
    owner_user, group
):
    grant = GroupMembershipGrant.objects.get(
        group=group.group_details, actor=owner_user, source_kind="manual"
    )
    grant.legacy_unclassified = True
    grant.save(update_fields=("legacy_unclassified",))
    with pytest.raises(RuntimeError, match="classifying every legacy grant"):
        ensure_exact_membership_ready()
    ensure_exact_membership_ready(retained_legacy_acknowledged=True)


@pytest.mark.parametrize("kind", [value for value, _label in KIND_CHOICES])
def test_policy_evaluator_uses_effective_grants_for_every_kind(
    kind, owner_user, owner_account, group
):
    resource = CatalogEntity.objects.create(
        kind=kind,
        name=f"owned-{kind}",
        owner=group,
    )
    assert policy_evaluator.check(owner_account, f"{kind}.edit", resource)
