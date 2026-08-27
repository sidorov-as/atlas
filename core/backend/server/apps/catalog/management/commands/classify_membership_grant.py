"""Classify or transfer one legacy membership grant, dry-run by default."""

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from server.apps.catalog.auth_policy import selected_provider
from server.apps.catalog.models import (
    ExternalIdentityLink,
    GroupMembershipGrant,
    MembershipGrantAuditRecord,
)


class Command(BaseCommand):
    help = (
        "Classify a legacy membership grant as retained manual access or "
        "transfer it to an exact external identity. Dry-run by default."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument("grant_id", type=int)
        parser.add_argument(
            "--as-manual",
            action="store_true",
            help=(
                "Acknowledge the grant as intentionally retained manual access."
            ),
        )
        parser.add_argument(
            "--identity-link-id",
            type=int,
            help="Transfer ownership to this exact external identity link.",
        )
        parser.add_argument(
            "--external-key",
            default="",
            help="Normalized external group key for a provider transfer.",
        )
        parser.add_argument("--reason", required=True)
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options) -> None:
        if options["as_manual"] == (options["identity_link_id"] is not None):
            raise CommandError(
                "Choose exactly one of --as-manual or --identity-link-id."
            )
        reason = options["reason"].strip()
        if not reason:
            raise CommandError("--reason must not be blank.")
        try:
            grant = GroupMembershipGrant.objects.select_related(
                "group__entity", "actor"
            ).get(pk=options["grant_id"])
        except GroupMembershipGrant.DoesNotExist as exc:
            raise CommandError("Membership grant not found.") from exc
        if not grant.legacy_unclassified:
            raise CommandError(
                "Only a legacy-unclassified grant can be classified."
            )

        link = None
        action = MembershipGrantAuditRecord.ACTION_CLASSIFY_MANUAL
        if options["identity_link_id"] is not None:
            if not options["external_key"].strip():
                raise CommandError(
                    "--external-key is required for provider transfer."
                )
            try:
                link = ExternalIdentityLink.objects.get(
                    pk=options["identity_link_id"], revoked_at__isnull=True
                )
            except ExternalIdentityLink.DoesNotExist as exc:
                raise CommandError(
                    "Active external identity link not found."
                ) from exc
            actor_account_id = getattr(
                grant.actor.actor_details, "account_id", None
            )
            if actor_account_id != link.user_id:
                raise CommandError(
                    "The identity link Principal is not linked to the grant "
                    "Actor."
                )
            action = MembershipGrantAuditRecord.ACTION_TRANSFER_PROVIDER

        target = "manual" if link is None else f"identity-link:{link.pk}"
        self.stdout.write(
            f"Grant {grant.pk}: {grant.actor.ref} -> {grant.group.entity.ref}; "
            f"legacy-unclassified -> {target}"
        )
        if not options["apply"]:
            self.stdout.write(
                self.style.WARNING("Dry run only — re-run with --apply.")
            )
            return

        with transaction.atomic():
            grant = GroupMembershipGrant.objects.select_for_update().get(
                pk=grant.pk
            )
            old_id = grant.pk
            if link is None:
                grant.legacy_unclassified = False
                grant.save(update_fields=("legacy_unclassified",))
            else:
                duplicate = (
                    GroupMembershipGrant.objects.filter(
                        group=grant.group,
                        actor=grant.actor,
                        source_kind=GroupMembershipGrant.SOURCE_PROVIDER,
                        identity_link=link,
                        external_key=options["external_key"].strip(),
                    )
                    .exclude(pk=grant.pk)
                    .first()
                )
                if duplicate is not None:
                    grant.delete()
                    grant = duplicate
                    policy = selected_provider(link.provider_id) or {}
                    group_sync = policy.get("groupSync", {})
                    if group_sync.get("mode") == "exact":
                        max_age = group_sync.get("maxAgeSeconds", 28_800)
                        grant.expires_at = timezone.now() + timedelta(
                            seconds=max_age
                        )
                    grant.revoked_at = None
                    grant.last_confirmed_at = timezone.now()
                    grant.save(
                        update_fields=(
                            "expires_at",
                            "revoked_at",
                            "last_confirmed_at",
                        )
                    )
                else:
                    grant.source_kind = GroupMembershipGrant.SOURCE_PROVIDER
                    grant.identity_link = link
                    grant.external_key = options["external_key"].strip()
                    grant.legacy_unclassified = False
                    policy = selected_provider(link.provider_id) or {}
                    group_sync = policy.get("groupSync", {})
                    if group_sync.get("mode") == "exact":
                        max_age = group_sync.get("maxAgeSeconds", 28_800)
                        grant.expires_at = timezone.now() + timedelta(
                            seconds=max_age
                        )
                    grant.last_confirmed_at = timezone.now()
                    grant.save()
            MembershipGrantAuditRecord.objects.create(
                grant_id=old_id,
                group_id=grant.group_id,
                actor_id=grant.actor_id,
                identity_link_id=link.pk if link else None,
                action=action,
                operator=None,
                reason=reason,
                details={"externalKey": grant.external_key or None},
            )
        self.stdout.write(
            self.style.SUCCESS(f"Classified membership grant {old_id}.")
        )
