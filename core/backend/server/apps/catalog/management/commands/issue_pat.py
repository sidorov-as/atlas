"""`manage.py issue_pat <username>` — issues an Atlas Personal Access Token
for `username` and prints the plaintext exactly once
(`personal-access-tokens` spec: "the plaintext value is displayed once in
that response, and no later request ... can retrieve it again").

The shell counterpart of the admin UI's "Add personal access token" form
(`PersonalAccessTokenAdmin.issue_view`); both go through
`issue_personal_access_token()`.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from server.apps.catalog.models import PersonalAccessToken
from server.apps.catalog.services.pat_service import issue_personal_access_token

User = get_user_model()

_VALID_SCOPES = {choice for choice, _label in PersonalAccessToken.SCOPE_CHOICES}


class Command(BaseCommand):
    help = (
        "Issue a new Atlas Personal Access Token for an existing user and "
        "print its plaintext value exactly once. The plaintext is never "
        "stored — save it now, it cannot be shown again."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "username",
            help="Exact username of the token's owner.",
        )
        parser.add_argument(
            "--name",
            default="",
            help="Optional human-readable label for the token.",
        )
        parser.add_argument(
            "--scope",
            dest="scopes",
            action="append",
            default=[],
            choices=sorted(_VALID_SCOPES),
            help=(
                "A scope to grant (repeatable). Scopes narrow, never "
                "broaden, the owner's own RBAC. Omit for a token with no "
                "scopes (can authenticate but authorize nothing)."
            ),
        )
        parser.add_argument(
            "--expires-in-days",
            dest="expires_in_days",
            type=int,
            default=None,
            help="Days until the token expires (default: never).",
        )

    def handle(self, *args, **options) -> None:
        username = options["username"]
        try:
            owner = User.objects.get(username=username)
        except User.DoesNotExist as exc:
            raise CommandError(f"No user with username={username!r}.") from exc

        expires_at = None
        if options["expires_in_days"] is not None:
            if options["expires_in_days"] <= 0:
                raise CommandError(
                    "--expires-in-days must be a positive integer."
                )
            expires_at = timezone.now() + timedelta(
                days=options["expires_in_days"]
            )

        issued = issue_personal_access_token(
            owner=owner,
            name=options["name"],
            scopes=options["scopes"],
            expires_at=expires_at,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Issued Personal Access Token id={issued.instance.pk} for "
                f"{owner.get_username()!r}"
            )
        )
        self.stdout.write(
            f"Scopes: {', '.join(issued.instance.scopes) or '(none)'}"
        )
        self.stdout.write(
            f"Expires: {issued.instance.expires_at or 'never'}",
        )
        self.stdout.write("")
        self.stdout.write(
            self.style.WARNING(
                "Token (shown once — save it now, it cannot be "
                "retrieved again):"
            )
        )
        self.stdout.write(issued.plaintext)
