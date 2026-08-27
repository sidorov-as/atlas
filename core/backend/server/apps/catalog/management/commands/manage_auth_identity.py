"""Inspect and mutate external identity links using exact identifiers."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from server.apps.catalog.models import (
    AuthenticationSourceBinding,
    ExternalIdentityLink,
    GroupMembershipGrant,
    ProvisioningAuditRecord,
)


class Command(BaseCommand):
    help = (
        "Inspect/link/revoke/restore/source-migrate an exact external identity"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "action",
            choices=("inspect", "link", "revoke", "restore", "source-migrate"),
        )
        parser.add_argument("--provider", required=True)
        parser.add_argument("--source", required=True)
        parser.add_argument("--subject")
        parser.add_argument("--principal-id", type=int)
        parser.add_argument("--to-source")
        parser.add_argument("--operator-id", type=int)
        parser.add_argument("--reason", default="")
        parser.add_argument("--privileged-target", action="store_true")
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        action = options["action"]
        query = ExternalIdentityLink.objects.filter(
            provider_id=options["provider"], source_id=options["source"]
        )
        if options["subject"]:
            query = query.filter(external_subject=options["subject"])
        if options["principal_id"]:
            query = query.filter(user_id=options["principal_id"])
        if action == "inspect":
            for link in query.order_by("pk"):
                self.stdout.write(
                    f"id={link.pk} principal={link.user_id} "
                    f"provider={link.provider_id} "
                    f"source={link.source_id} subject={link.external_subject} "
                    f"revoked={link.revoked_at is not None} "
                    f"generation={link.revocation_generation}"
                )
            return

        if not options["subject"]:
            raise CommandError("--subject is required for mutations")
        if not options["reason"]:
            raise CommandError("--reason is required for mutations")
        operator = None
        if options["operator_id"]:
            operator = get_user_model().objects.get(pk=options["operator_id"])

        if action == "link":
            if not options["principal_id"]:
                raise CommandError("--principal-id is required for link")
            principal = get_user_model().objects.get(pk=options["principal_id"])
            if (principal.is_staff or principal.is_superuser) and not options[
                "privileged_target"
            ]:
                raise CommandError(
                    "administrative Principal requires --privileged-target"
                )
            identity = (
                f"{options['provider']}:{options['source']}:"
                f"{options['subject']}"
            )
            preview = f"link {identity} -> Principal {principal.pk}"
        elif action == "source-migrate":
            if not options["to_source"]:
                raise CommandError("--to-source is required for source-migrate")
            preview = (
                f"migrate {query.count()} link(s) to source "
                f"{options['to_source']}"
            )
        else:
            if query.count() != 1:
                raise CommandError(
                    f"expected exactly one link, found {query.count()}"
                )
            preview = f"{action} link {query.get().pk}"

        self.stdout.write(
            f"DRY RUN: {preview}"
            if not options["apply"]
            else f"APPLY: {preview}"
        )
        if not options["apply"]:
            return

        with transaction.atomic():
            if action == "link":
                link, created = ExternalIdentityLink.objects.get_or_create(
                    provider_id=options["provider"],
                    source_id=options["source"],
                    external_subject=options["subject"],
                    defaults={"user": principal},
                )
                if not created and link.user_id != principal.pk:
                    raise CommandError(
                        "identity is already linked to another Principal"
                    )
                if not created and link.revoked_at is not None:
                    raise CommandError(
                        "identity link is revoked; use the explicit "
                        "restore action"
                    )
            elif action == "source-migrate":
                links = list(query.select_for_update())
                for link in links:
                    if (
                        ExternalIdentityLink.objects.filter(
                            provider_id=link.provider_id,
                            source_id=options["to_source"],
                            external_subject=link.external_subject,
                        )
                        .exclude(pk=link.pk)
                        .exists()
                    ):
                        raise CommandError(
                            f"target identity collision for link {link.pk}"
                        )
                old_binding = (
                    AuthenticationSourceBinding.objects.select_for_update()
                    .filter(
                        provider_id=options["provider"],
                        source_id=options["source"],
                    )
                    .first()
                )
                if old_binding is not None:
                    target_binding, created = (
                        AuthenticationSourceBinding.objects.get_or_create(
                            provider_id=old_binding.provider_id,
                            source_id=options["to_source"],
                            defaults={
                                "configuration_fingerprint": (
                                    old_binding.configuration_fingerprint
                                ),
                                "lock_digest": old_binding.lock_digest,
                                "generation": old_binding.generation + 1,
                            },
                        )
                    )
                    if (
                        not created
                        and target_binding.configuration_fingerprint
                        != old_binding.configuration_fingerprint
                    ):
                        raise CommandError(
                            "target source binding has a different fingerprint"
                        )
                    if target_binding.revoked_at is not None:
                        raise CommandError("target source binding is revoked")
                    old_binding.revoked_at = timezone.now()
                    old_binding.generation += 1
                    old_binding.save(update_fields=("revoked_at", "generation"))
                for link in links:
                    link.source_id = options["to_source"]
                    link.save(update_fields=("source_id",))
                    self._audit("source_migrated", link, operator, options)
                return
            else:
                link = query.select_for_update().get()
                if action == "revoke":
                    link.revoked_at = timezone.now()
                    link.revocation_generation += 1
                    GroupMembershipGrant.objects.filter(
                        identity_link=link
                    ).update(revoked_at=link.revoked_at)
                elif action == "restore":
                    link.revoked_at = None
                    link.revocation_generation += 1
                    # Grants remain revoked: restore never resurrects access.
                link.save(update_fields=("revoked_at", "revocation_generation"))
            self._audit(action, link, operator, options)

    @staticmethod
    def _audit(action, link, operator, options):
        details = {"reason": options["reason"]}
        if action == "source_migrated":
            details.update(
                {
                    "fromSourceId": options["source"],
                    "toSourceId": options["to_source"],
                }
            )
        ProvisioningAuditRecord.objects.create(
            action=f"identity_{action}",
            provider_id=link.provider_id,
            source_id=link.source_id,
            principal_id=link.user_id,
            identity_link_id=link.pk,
            correlation_id="operator-command",
            operator=operator,
            details=details,
        )
