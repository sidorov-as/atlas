"""Controlled first-boot bootstrap for a local administrator.

Group/Actor have no creation API (they are seeded outside the
API), so without this the stack has nowhere for an owner Group to come from
and nobody who could log in to create one via the admin.
Idempotent: safe to run on every boot.
"""

import getpass
import os
import sys

from atlas_plugin_api import KIND_ACTOR, KIND_GROUP, get_catalog_entity_model
from atlas_plugin_standard_catalog.models import ActorDetails, GroupDetails
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


@transaction.atomic
def bootstrap_administrator(*, username: str, password: str, email: str, group: str):
    """Create/update the exact bootstrap account and its catalog linkage."""

    auth_user_model = get_user_model()
    catalog_entity_model = get_catalog_entity_model()
    account, created = auth_user_model.objects.get_or_create(
        username=username,
        defaults={"email": email, "is_staff": True, "is_superuser": True},
    )
    validate_password(password, user=account)
    account.email = email
    account.is_active = True
    account.is_staff = True
    account.is_superuser = True
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
            title=group.title(),
        )
        GroupDetails.objects.create(entity=group_entity, type="root")

    actor_details = (
        ActorDetails.objects.filter(
            account=account,
        )
        .select_related("entity")
        .first()
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
    help = "Seed a first owner Group and a superuser, so the stack is usable after first boot."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--username", default="admin")
        parser.add_argument("--email", default="admin@example.com")
        parser.add_argument(
            "--group", default="platform", help="Name of the seed owner Group."
        )
        parser.add_argument(
            "--password-env",
            default="ATLAS_BOOTSTRAP_PASSWORD",
            help="Environment variable containing the password.",
        )
        parser.add_argument(
            "--password-stdin",
            action="store_true",
            help="Read the password from standard input without echoing it.",
        )

    def handle(self, *args, **options) -> None:
        if options["password_stdin"]:
            password = sys.stdin.readline().rstrip("\n")
        else:
            password = os.environ.get(options["password_env"])
            if password is None and sys.stdin.isatty():
                password = getpass.getpass("Bootstrap administrator password: ")
        if not password:
            raise CommandError(
                "Provide the bootstrap secret through --password-stdin or "
                f"the {options['password_env']} environment variable.",
            )
        account, created = bootstrap_administrator(
            username=options["username"],
            password=password,
            email=options["email"],
            group=options["group"],
        )
        action = "Created" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} bootstrap administrator {account.username!r}",
            )
        )
