"""Public collaboration contract for Principal-to-Actor provisioning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ActorReference:
    id: UUID
    name: str

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID):
            raise TypeError("Actor id must be a UUID")
        if not self.name or self.name != self.name.strip():
            raise ValueError("Actor name must be non-empty and normalized")


@dataclass(frozen=True, slots=True)
class ActorProvisioningRequest:
    principal_id: int
    proposed_name: str
    display_name: str = ""
    email: str = ""
    provenance: str = "authentication-provider"
    correlation_id: str = ""

    def __post_init__(self) -> None:
        if self.principal_id <= 0:
            raise ValueError("Principal id must be positive")
        if not self.proposed_name or self.proposed_name != self.proposed_name.strip():
            raise ValueError("proposed Actor name must be non-empty and normalized")
        if not self.provenance or self.provenance != self.provenance.strip():
            raise ValueError("Actor provenance must be non-empty and normalized")
        if (
            not self.correlation_id
            or self.correlation_id != self.correlation_id.strip()
        ):
            raise ValueError("correlation id must be non-empty and normalized")


@dataclass(frozen=True, slots=True)
class ActorProvisioningResult:
    actor: ActorReference
    created: bool
    linked: bool


class ActorProvisioningService(Protocol):
    def resolve_for_principal(self, principal_id: int) -> ActorReference | None: ...

    def ensure_for_principal(
        self, request: ActorProvisioningRequest
    ) -> ActorProvisioningResult: ...

    def link_existing(
        self, *, principal_id: int, actor_id: UUID, correlation_id: str
    ) -> ActorProvisioningResult: ...

    def update_profile(
        self,
        *,
        principal_id: int,
        display_name: str | None,
        email: str | None,
    ) -> ActorReference | None: ...


_actor_provisioning_service: ActorProvisioningService | None = None
_actor_provisioning_owner: str | None = None


def bind_actor_provisioning_service(
    service: ActorProvisioningService, *, owner: str
) -> None:
    global _actor_provisioning_service, _actor_provisioning_owner
    if _actor_provisioning_service is not None and _actor_provisioning_owner != owner:
        raise RuntimeError(
            "Actor provisioning service is already bound by "
            f"{_actor_provisioning_owner!r}; duplicate owner {owner!r}"
        )
    _actor_provisioning_service = service
    _actor_provisioning_owner = owner


def get_actor_provisioning_service() -> ActorProvisioningService:
    if _actor_provisioning_service is None:
        raise RuntimeError("Actor provisioning service is not registered")
    return _actor_provisioning_service
