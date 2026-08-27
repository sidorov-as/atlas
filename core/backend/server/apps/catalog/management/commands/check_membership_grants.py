"""Report legacy grants that block safe activation of exact group sync."""

from django.core.management.base import BaseCommand, CommandError

from server.apps.catalog.membership import ensure_exact_membership_ready
from server.apps.catalog.models import GroupMembershipGrant


class Command(BaseCommand):
    help = (
        "Check whether all legacy membership grants have been classified "
        "before exact group synchronization is enabled."
    )

    def handle(self, *args, **options) -> None:
        unclassified = GroupMembershipGrant.objects.filter(
            legacy_unclassified=True
        ).select_related("group__entity", "actor")
        for grant in unclassified.iterator():
            self.stdout.write(
                f"grant={grant.pk} actor={grant.actor.ref} "
                f"group={grant.group.entity.ref}"
            )
        try:
            ensure_exact_membership_ready()
        except RuntimeError as exc:
            raise CommandError(
                f"Exact synchronization is not ready: "
                f"{unclassified.count()} legacy grant(s) require review."
            ) from exc
        self.stdout.write(
            self.style.SUCCESS(
                "Exact synchronization readiness check passed: no "
                "legacy-unclassified grants remain."
            )
        )
