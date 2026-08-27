"""`manage.py clear_read_only <username>` — infrastructure-only recovery for
an AccountAccess lockout (all writable administrators are unavailable).

Django admin intentionally has no path to remove a read-only flag except a
non-read-only operator with the AccountAccess change permission
(`server.apps.catalog.admin.AccountAccessInline`); if every such operator is
itself locked out, that's a genuine dead end from the web UI by design. This
command is the documented escape hatch — it requires shell/infrastructure
access (like `purge_plugin`), not a browser session, so it cannot become a
callable web bypass for a read-only session.

Defaults to a dry run reporting the exact account and its current/proposed
state; only `--confirm` actually writes. `--reason` is mandatory so the
audit record (`AccountAccessAuditRecord`, the same trail
`UserAdmin.save_formset` writes to) always explains why an operator bypassed
normal admin authorization.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from server.apps.catalog.models import AccountAccess, AccountAccessAuditRecord

User = get_user_model()


class Command(BaseCommand):
    help = (
        "Clear (or set) an account's read_only flag from infrastructure "
        "access, for when every non-read-only administrator is locked out. "
        "Dry run by default; pass --confirm to actually write. Requires "
        "--reason."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "username",
            help="Exact username of the target account.",
        )
        parser.add_argument(
            "--reason",
            required=True,
            help=(
                "Why this recovery is being performed. Recorded in "
                "the audit trail."
            ),
        )
        parser.add_argument(
            "--set",
            dest="read_only",
            choices=("true", "false"),
            default="false",
            help=(
                "Value to set read_only to (default: 'false', the "
                "recovery case)."
            ),
        )
        parser.add_argument(
            "--confirm",
            action="store_true",
            help=(
                "Actually write the change. Without this, only the "
                "intended change is reported."
            ),
        )

    def handle(self, *args, **options) -> None:
        username = options["username"]
        new_read_only = options["read_only"] == "true"
        reason = options["reason"].strip()
        if not reason:
            raise CommandError("--reason must not be blank.")

        try:
            target = User.objects.get(username=username)
        except User.DoesNotExist as exc:
            raise CommandError(f"No user with username={username!r}.") from exc

        access = AccountAccess.objects.filter(account=target).first()
        old_read_only = access.read_only if access else False

        self.stdout.write(
            f"Target: {target.get_username()!r} (id={target.pk}) "
            f"read_only: {old_read_only} -> {new_read_only}",
        )
        self.stdout.write(f"Reason: {reason}")

        if not options["confirm"]:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "Dry run only — no change written. "
                    "Re-run with --confirm to apply.",
                )
            )
            return

        if old_read_only == new_read_only:
            self.stdout.write(
                self.style.WARNING(
                    "Already at the requested value — no change made, "
                    "nothing audited.",
                )
            )
            return

        with transaction.atomic():
            is_new = access is None
            if access is None:
                access = AccountAccess(account=target)
            access.read_only = new_read_only
            access.save()
            AccountAccessAuditRecord.objects.create(
                target_id=target.pk,
                target_username=target.get_username(),
                operator=None,
                action=(
                    AccountAccessAuditRecord.ACTION_CREATE
                    if is_new
                    else AccountAccessAuditRecord.ACTION_UPDATE
                ),
                old_read_only=old_read_only,
                new_read_only=new_read_only,
                reason=f"[infrastructure recovery] {reason}",
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Set read_only={new_read_only} for {username!r}.",
            )
        )
