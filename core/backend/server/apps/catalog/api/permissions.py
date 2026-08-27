"""Ownership permission checks for entity writes.

Safe methods (list/retrieve) only need `SessionAuth`, applied at the controller
level — no ownership restriction. Writes (create/update/delete) additionally go
through `EntityWritePermission`: superusers always pass, and everyone else must
be a member (via their linked `ActorDetails.account`) of the Group in
question. YAML-managed entities reject every write, superuser included, since
provenance (not permission) is what blocks them (ADR 0001).

The ownership-membership rule itself now lives in `server.apps.catalog.
authorization` behind the built-in RBAC
`PolicyEvaluator`, not here — `check_write` and `check_adopt` request an edit
decision from it once a `resource` exists; `check_create` has no resource yet
(only an intended owner Group), so it calls the shared membership rule
directly.

Checks take the acting Django user directly (not the `HttpRequest`) so the
core Entity Service's `authorize` step can call them with
whatever `actor` it was given, independent of any particular request.
"""

from http import HTTPStatus

from django.contrib.auth.base_user import AbstractBaseUser
from django.http import HttpRequest
from dmr.errors import ErrorType, format_error
from dmr.response import APIError

from server.apps.catalog.authorization import (
    is_account_read_only,
    is_group_member,
    policy_evaluator,
)
from server.apps.catalog.models import CatalogEntity


def _forbidden(message: str) -> APIError:
    return APIError(
        format_error(message, error_type=ErrorType.security),
        status_code=HTTPStatus.FORBIDDEN,
    )


class EntityWritePermission:
    """Enforces the ownership rule for entity writes."""

    @classmethod
    def check_create(
        cls, user: AbstractBaseUser, owner: CatalogEntity | None
    ) -> None:
        """Resource-less create has no `resource` yet to route through
        `policy_evaluator.check(...)`, so it's one of the direct-check
        sites `CoreGuardedEvaluator` can't wrap (resource-less entity
        creation) —
        the read-only guard is applied here explicitly, before
        `is_group_member`, so membership state itself is never touched or
        needs to change for the write to be denied.
        """
        if is_account_read_only(user):
            raise _forbidden("Your account is read-only")
        if not is_group_member(user, owner):
            raise _forbidden("You are not a member of the owner Group")

    @classmethod
    def check_write(
        cls, user: AbstractBaseUser, instance: CatalogEntity
    ) -> None:
        if instance.source_kind == CatalogEntity.SOURCE_YAML:
            raise _forbidden(
                "This entity is managed by catalog-info.yaml and is read-only"
            )
        if not policy_evaluator.check(user, f"{instance.kind}.edit", instance):
            raise _forbidden("You are not a member of the owner Group")

    @classmethod
    def check_adopt(
        cls, user: AbstractBaseUser, instance: CatalogEntity
    ) -> None:
        if instance.source_kind == CatalogEntity.SOURCE_YAML:
            raise _forbidden(
                "This entity is already managed by catalog-info.yaml "
                "and cannot be adopted again"
            )
        if not policy_evaluator.check(user, f"{instance.kind}.edit", instance):
            raise _forbidden("You are not a member of the owner Group")

    @classmethod
    def check_purge(
        cls, user: AbstractBaseUser, instance: CatalogEntity
    ) -> None:
        """Purge Grant, not the `source_kind=yaml` block: unlike `check_write`/
        `check_adopt`, a YAML-managed entity is deliberately purgeable by a
        grant holder (purgeable despite the general manual-write block; a narrow
        carve-out)."""
        if not policy_evaluator.check(user, f"{instance.kind}.purge", instance):
            raise _forbidden(
                "You do not hold a Purge Grant for this entity's owner Group"
            )


class TagWritePermission:
    """Enforces superuser-only writes for tag color updates.

    Tag color is global config with no natural owning Group, so unlike entity
    writes it isn't gated by group membership — reads follow the existing "any
    authenticated user" rule and only writes require `is_superuser`.
    """

    @staticmethod
    def check_write(request: HttpRequest) -> None:
        if is_account_read_only(request.user):
            raise _forbidden("Your account is read-only")
        if not request.user.is_superuser:
            raise _forbidden("Only superusers can update tag colors")


class CatalogHomeSettingsWritePermission:
    """Enforces superuser-only writes for the "About this catalog" content

    Mirrors `TagWritePermission.check_write` exactly: global config with no
    owning Group, reads open to any authenticated user, writes superuser-only.
    """

    @staticmethod
    def check_write(request: HttpRequest) -> None:
        if is_account_read_only(request.user):
            raise _forbidden("Your account is read-only")
        if not request.user.is_superuser:
            raise _forbidden(
                "Only superusers can update the catalog home settings"
            )
