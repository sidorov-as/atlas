"""Shared source-aware Group membership reads and writes."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import timedelta
from typing import Any, cast

from atlas_plugin_api import recompute_relations
from django.db import transaction
from django.db.models import Q, QuerySet
from django.db.models.functions import Now
from django.utils import timezone

from .auth_policy import authentication_policy, provider_source_id
from .models import CatalogEntity, ExternalIdentityLink, GroupMembershipGrant


def _applicable_provider_grants() -> Q:
    applicable = Q(pk__in=[])
    for provider in authentication_policy().get("providers", ()):
        provider_id = provider.get("id")
        source_id = provider_source_id(provider)
        group_sync = provider.get("groupSync", {})
        mode = group_sync.get("mode")
        if (
            not provider_id
            or not source_id
            or mode not in {"additive", "exact"}
        ):
            continue
        provider_q = Q(
            source_kind=GroupMembershipGrant.SOURCE_PROVIDER,
            identity_link__provider_id=provider_id,
            identity_link__source_id=source_id,
            identity_link__revoked_at__isnull=True,
        )
        if mode == "exact":
            max_age = group_sync.get("maxAgeSeconds", 28_800)
            if not isinstance(max_age, int) or max_age <= 0:
                continue
            provider_q &= Q(expires_at__gt=Now()) & Q(
                last_confirmed_at__gt=Now() - timedelta(seconds=max_age)
            )
        else:
            provider_q &= Q(expires_at__isnull=True)
        applicable |= provider_q
    return applicable


def effective_grants(
    *,
    actor: CatalogEntity | None = None,
    group: Any | None = None,
) -> QuerySet[GroupMembershipGrant]:
    """Return grants applicable under current time and selected auth policy."""

    queryset = GroupMembershipGrant.objects.filter(revoked_at__isnull=True)
    if actor is not None:
        queryset = queryset.filter(actor=actor)
    if group is not None:
        group_id = getattr(group, "entity_id", getattr(group, "pk", group))
        queryset = queryset.filter(group_id=group_id)
    return queryset.filter(
        Q(source_kind=GroupMembershipGrant.SOURCE_MANUAL)
        | _applicable_provider_grants()
    )


def effective_members(group: Any) -> QuerySet[CatalogEntity]:
    grant_actor_ids = effective_grants(group=group).values("actor_id")
    return CatalogEntity.objects.filter(pk__in=grant_actor_ids)


def effective_groups(actor: CatalogEntity) -> QuerySet[CatalogEntity]:
    grant_group_ids = effective_grants(actor=actor).values("group_id")
    return CatalogEntity.objects.filter(pk__in=grant_group_ids)


def is_effective_member(*, actor: CatalogEntity, group: Any) -> bool:
    return effective_grants(actor=actor, group=group).exists()


def set_manual_memberships(group: Any, actors: Iterable[CatalogEntity]) -> None:
    """Replace only manual grants, preserving every provider-owned grant."""

    actors_by_id = {actor.pk: actor for actor in actors}
    actor_ids = set(actors_by_id)
    now = timezone.now()
    with transaction.atomic():
        current = GroupMembershipGrant.objects.select_for_update().filter(
            group=group,
            source_kind=GroupMembershipGrant.SOURCE_MANUAL,
        )
        current.exclude(actor_id__in=actor_ids).delete()
        existing = set(current.values_list("actor_id", flat=True))
        GroupMembershipGrant.objects.bulk_create(
            [
                GroupMembershipGrant(
                    group=group,
                    actor_id=actor_id,
                    source_kind=GroupMembershipGrant.SOURCE_MANUAL,
                    last_confirmed_at=now,
                )
                for actor_id in actor_ids - existing
            ]
        )
    recompute_relations(group.entity)
    for actor in actors_by_id.values():
        recompute_relations(actor)


def add_manual_membership(
    *, group: Any, actor: CatalogEntity
) -> GroupMembershipGrant:
    grant, _created = GroupMembershipGrant.objects.get_or_create(
        group=group,
        actor=actor,
        source_kind=GroupMembershipGrant.SOURCE_MANUAL,
        defaults={"last_confirmed_at": timezone.now()},
    )
    recompute_relations(group.entity)
    recompute_relations(actor)
    return grant


def remove_manual_membership(*, group: Any, actor: CatalogEntity) -> bool:
    deleted, _details = GroupMembershipGrant.objects.filter(
        group=group,
        actor=actor,
        source_kind=GroupMembershipGrant.SOURCE_MANUAL,
    ).delete()
    recompute_relations(group.entity)
    recompute_relations(actor)
    return bool(deleted)


def add_provider_membership(
    *,
    group: Any,
    actor: CatalogEntity,
    identity_link: ExternalIdentityLink,
    external_key: str,
    expires_at=None,
) -> GroupMembershipGrant:
    now = timezone.now()
    grant, _created = GroupMembershipGrant.objects.update_or_create(
        group=group,
        actor=actor,
        identity_link=identity_link,
        external_key=external_key,
        defaults={
            "source_kind": GroupMembershipGrant.SOURCE_PROVIDER,
            "legacy_unclassified": False,
            "expires_at": expires_at,
            "revoked_at": None,
            "last_confirmed_at": now,
        },
    )
    recompute_relations(group.entity)
    recompute_relations(actor)
    return grant


def membership_grant_summaries(
    *, group: Any, actor: CatalogEntity
) -> list[dict[str, Any]]:
    applicable_ids = set(
        effective_grants(group=group, actor=actor).values_list("pk", flat=True)
    )
    grants = GroupMembershipGrant.objects.filter(
        group=group, actor=actor
    ).select_related("identity_link")
    return [
        {
            "id": grant.pk,
            "sourceKind": grant.source_kind,
            "providerId": grant.identity_link.provider_id
            if grant.identity_link
            else None,
            "sourceId": grant.identity_link.source_id
            if grant.identity_link
            else None,
            "subject": grant.identity_link.external_subject
            if grant.identity_link
            else None,
            "externalKey": grant.external_key or None,
            "legacyUnclassified": grant.legacy_unclassified,
            "createdAt": grant.created_at,
            "lastConfirmedAt": grant.last_confirmed_at,
            "expiresAt": grant.expires_at,
            "applicable": grant.pk in applicable_ids,
        }
        for grant in grants
    ]


def has_unclassified_legacy_grants() -> bool:
    return GroupMembershipGrant.objects.filter(
        legacy_unclassified=True
    ).exists()


def ensure_exact_membership_ready(
    *, retained_legacy_acknowledged: bool = False
) -> None:
    if has_unclassified_legacy_grants() and not retained_legacy_acknowledged:
        raise RuntimeError(
            "Exact group synchronization requires classifying every legacy "
            "grant or explicitly acknowledging retained legacy access."
        )


def group_memberships(group: Any) -> list[dict[str, Any]]:
    actor_ids = GroupMembershipGrant.objects.filter(group=group).values(
        "actor_id"
    )
    actors = CatalogEntity.objects.filter(pk__in=actor_ids)
    return [
        {
            "actor": actor,
            "effective": is_effective_member(actor=actor, group=group),
            "grants": membership_grant_summaries(group=group, actor=actor),
        }
        for actor in actors
    ]


def actor_memberships(actor: CatalogEntity) -> list[dict[str, Any]]:
    group_ids = GroupMembershipGrant.objects.filter(actor=actor).values(
        "group_id"
    )
    groups = CatalogEntity.objects.filter(pk__in=group_ids)
    return [
        {
            "group": group,
            "effective": is_effective_member(
                actor=actor, group=cast(Any, group).group_details
            ),
            "grants": membership_grant_summaries(
                group=cast(Any, group).group_details, actor=actor
            ),
        }
        for group in groups
    ]


class DjangoMembershipService:
    def effective_members(self, group: Any):
        return effective_members(group)

    def effective_groups(self, actor: Any):
        return effective_groups(actor)

    def set_manual_memberships(self, group: Any, actors: Iterable[Any]) -> None:
        set_manual_memberships(group, actors)

    def grant_summaries(
        self, *, group: Any, actor: Any
    ) -> list[dict[str, Any]]:
        return membership_grant_summaries(group=group, actor=actor)

    def group_memberships(self, group: Any) -> list[dict[str, Any]]:
        return group_memberships(group)

    def actor_memberships(self, actor: Any) -> list[dict[str, Any]]:
        return actor_memberships(actor)


membership_service = DjangoMembershipService()
