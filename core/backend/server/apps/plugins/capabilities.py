"""Capability registry.

Named, versioned service contracts one plugin publishes and another
consumes by id (plugin-architecture.md "Service capabilities"). No plugin
registers a capability yet — the
registry exists so the runtime load phase and composition validation have
a stable target for the first real consumer.

`resolve` returns a typed `CapabilityResult` rather than `object
| None`, so a consumer can't mistake "no plugin registered this capability"
for a successful call that happens to return a falsy/empty value.
"""

from server.apps.catalog.kinds import CapabilityResult, Ok, Unavailable


class DuplicateCapabilityError(ValueError):
    """Raised when a second plugin tries to register a claimed `capability_id`.

    `existing_owner`/`new_owner` carry the registering plugins' ids, when
    known, for composition-validation error reporting.
    """

    def __init__(
        self,
        capability_id: str,
        *,
        existing_owner: str | None = None,
        new_owner: str | None = None,
    ) -> None:
        message = (
            f"A capability is already registered for "
            f"capability_id={capability_id!r}"
        )
        if existing_owner or new_owner:
            message += (
                f" (already registered by {existing_owner!r}, "
                f"conflicting registration from {new_owner!r})"
            )
        super().__init__(message)
        self.capability_id = capability_id
        self.existing_owner = existing_owner
        self.new_owner = new_owner


class CapabilityRegistry:
    """Maps `capability_id` to its registered service-contract."""

    def __init__(self) -> None:
        self._capabilities: dict[str, object] = {}
        self._owners: dict[str, str | None] = {}

    def register(
        self,
        capability_id: str,
        implementation: object,
        *,
        owner: str | None = None,
    ) -> None:
        if capability_id in self._capabilities:
            raise DuplicateCapabilityError(
                capability_id,
                existing_owner=self._owners[capability_id],
                new_owner=owner,
            )
        self._capabilities[capability_id] = implementation
        self._owners[capability_id] = owner

    def resolve(self, capability_id: str) -> CapabilityResult[object]:
        """Return `Ok(implementation)` for `capability_id`, or `Unavailable`
        if no plugin has registered it."""
        if capability_id not in self._capabilities:
            return Unavailable()
        return Ok(self._capabilities[capability_id])

    def registered_ids(self) -> list[str]:
        """Return every registered `capability_id`, sorted."""
        return sorted(self._capabilities)


# Process-wide registry populated by the runtime entry-point-loading phase.
registry = CapabilityRegistry()
