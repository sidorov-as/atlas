"""Public collaboration seam for source-aware catalog membership."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol


class MembershipService(Protocol):
    def effective_members(self, group: Any) -> Any: ...

    def effective_groups(self, actor: Any) -> Any: ...

    def set_manual_memberships(self, group: Any, actors: Iterable[Any]) -> None: ...

    def grant_summaries(self, *, group: Any, actor: Any) -> list[dict[str, Any]]: ...

    def group_memberships(self, group: Any) -> list[dict[str, Any]]: ...

    def actor_memberships(self, actor: Any) -> list[dict[str, Any]]: ...


_membership_service: MembershipService | None = None


def bind_membership_service(service: MembershipService) -> None:
    global _membership_service
    _membership_service = service


def get_membership_service() -> MembershipService:
    if _membership_service is None:
        raise RuntimeError(
            "get_membership_service() called before Core registered its service"
        )
    return _membership_service


def get_membership_grant_model() -> type:
    from django.apps import apps

    return apps.get_model("catalog", "GroupMembershipGrant")
