"""Bootstrap an unprivileged demo user in its own owner Group.

The account is neither staff nor superuser: it can read the whole catalog and
create/edit entities owned by its own Group, but cannot modify anyone else's
(RBAC ownership rule, ADR 0016). Meant for public demos where the
administrator credentials stay private.
Idempotent: safe to run on every boot.
"""

import os

from atlas_plugin_api import KIND_ACTOR, KIND_GROUP, get_catalog_entity_model
from atlas_plugin_standard_catalog.models import ActorDetails, GroupDetails
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


@transaction.atomic
def bootstrap_guest(*, username: str, password: str, email: str, group: str):
    """Create/update the guest account, its Actor and its own Group."""

    auth_user_model = get_user_model()
    catalog_entity_model = get_catalog_entity_model()
    account, created = auth_user_model.objects.get_or_create(
        username=username,
        defaults={"email": email},
    )
    validate_password(password, user=account)
    account.email = email
    account.is_active = True
    account.is_staff = False
    account.is_superuser = False
    account.set_password(password)
    account.save()

    group_entity = catalog_entity_model.objects.filter(
        kind=KIND_GROUP,
        name=group,
    ).first()
    if group_entity is None:
        group_entity = catalog_entity_model.objects.create(
            kind=KIND_GROUP,
            name=group,
            title=group.replace("-", " ").title(),
        )
        GroupDetails.objects.create(entity=group_entity, type="team")

    actor_details = (
        ActorDetails.objects.filter(account=account).select_related("entity").first()
    )
    if actor_details is None:
        actor_entity = catalog_entity_model.objects.create(
            kind=KIND_ACTOR,
            name=account.username,
        )
        actor_details = ActorDetails.objects.create(
            entity=actor_entity,
            account=account,
            display_name=account.username,
            email=account.email,
        )
    group_entity.group_details.members.add(actor_details.entity)
    return account, created


class Command(BaseCommand):
    help = "Seed an unprivileged demo user that owns its own Group."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--username", default="guest")
        parser.add_argument("--email", default="guest@example.com")
        parser.add_argument("--group", default="guest-team")
        parser.add_argument(
            "--password-env",
            default="ATLAS_DEMO_GUEST_PASSWORD",
            help="Environment variable containing the password.",
        )

    def handle(self, *args, **options) -> None:
        password = os.environ.get(options["password_env"])
        if not password:
            raise CommandError(
                f"Set the {options['password_env']} environment variable.",
            )
        account, created = bootstrap_guest(
            username=options["username"],
            password=password,
            email=options["email"],
            group=options["group"],
        )
        action = "Created" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(f"{action} guest user {account.username!r}"),
        )
