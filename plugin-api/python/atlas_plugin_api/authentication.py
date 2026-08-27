"""Public authentication-provider contracts (``atlas.auth.providers.v1``).

This module is deliberately implementation-free.  It defines the static and
runtime values shared by provider plugins and Authentication Core, but imports
neither Django nor Core.  Providers verify credentials or redirect protocols;
Core owns selection, provisioning, sessions, CSRF, and authorization.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Literal, Protocol, runtime_checkable

from .config import PluginConfigSchema

AUTHENTICATION_PROVIDER_CONTRACT_V1: Literal["atlas.auth.providers.v1"] = (
    "atlas.auth.providers.v1"
)

type AuthenticationProviderId = str
type AuthenticationProviderContractVersion = Literal["atlas.auth.providers.v1"]


def _require_non_empty(value: str, field_name: str) -> str:
    if not value or value != value.strip():
        raise ValueError(f"{field_name} must be non-empty and normalized")
    return value


def _freeze_string_mapping(
    values: Mapping[str, str],
    *,
    field_name: str,
    allow_empty_values: bool,
) -> Mapping[str, str]:
    frozen: dict[str, str] = {}
    for key, value in values.items():
        _require_non_empty(key, f"{field_name} key")
        if not allow_empty_values:
            _require_non_empty(value, f"{field_name}[{key!r}]")
        frozen[key] = value
    return MappingProxyType(frozen)


class AuthenticationFlowKind(StrEnum):
    CREDENTIALS = "credentials"
    REDIRECT = "redirect"


class RemoteLogoutCapability(StrEnum):
    UNSUPPORTED = "unsupported"
    SUPPORTED = "supported"


class CredentialFieldKind(StrEnum):
    TEXT = "text"
    SECRET = "secret"


@dataclass(frozen=True, slots=True)
class CredentialFieldPresentation:
    """Safe frontend metadata for one standard credential input."""

    id: str
    label: str
    kind: CredentialFieldKind
    autocomplete: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.id, "credential field id")
        _require_non_empty(self.label, "credential field label")
        if not isinstance(self.kind, CredentialFieldKind):
            raise TypeError(f"unsupported credential field kind: {self.kind!r}")
        if self.autocomplete is not None:
            _require_non_empty(self.autocomplete, "credential field autocomplete")


@dataclass(frozen=True, slots=True)
class AuthenticationProviderPresentation:
    """Provider metadata that is explicitly safe to expose before login."""

    display_name: str
    credential_fields: tuple[CredentialFieldPresentation, ...] = ()

    def __post_init__(self) -> None:
        _require_non_empty(self.display_name, "provider display name")
        ids = [item.id for item in self.credential_fields]
        if len(ids) != len(set(ids)):
            raise ValueError("credential field ids must be unique")


@dataclass(frozen=True, slots=True)
class AuthenticationProviderDescriptor:
    """Static identity and flow capabilities for one provider implementation."""

    id: AuthenticationProviderId
    flow_kind: AuthenticationFlowKind
    presentation: AuthenticationProviderPresentation
    contract_version: AuthenticationProviderContractVersion = (
        AUTHENTICATION_PROVIDER_CONTRACT_V1
    )
    remote_logout: RemoteLogoutCapability = RemoteLogoutCapability.UNSUPPORTED

    def __post_init__(self) -> None:
        _require_non_empty(self.id, "provider id")
        if not isinstance(self.flow_kind, AuthenticationFlowKind):
            raise TypeError(f"unsupported authentication flow kind: {self.flow_kind!r}")
        if not isinstance(self.presentation, AuthenticationProviderPresentation):
            raise TypeError("presentation must be AuthenticationProviderPresentation")
        if self.contract_version != AUTHENTICATION_PROVIDER_CONTRACT_V1:
            raise ValueError(
                f"unsupported authentication provider contract version: "
                f"{self.contract_version!r}",
            )
        if not isinstance(self.remote_logout, RemoteLogoutCapability):
            raise TypeError(
                f"unsupported remote logout capability: {self.remote_logout!r}"
            )
        if (
            self.flow_kind is AuthenticationFlowKind.REDIRECT
            and self.presentation.credential_fields
        ):
            raise ValueError("redirect providers cannot declare credential fields")
        if (
            self.flow_kind is AuthenticationFlowKind.CREDENTIALS
            and not self.presentation.credential_fields
        ):
            raise ValueError("credential providers must declare credential fields")
        if (
            self.flow_kind is AuthenticationFlowKind.CREDENTIALS
            and self.remote_logout is RemoteLogoutCapability.SUPPORTED
        ):
            raise ValueError("remote logout is supported only by redirect providers")


@dataclass(frozen=True, slots=True)
class AuthenticationProviderContribution:
    """Django-setup-safe provider metadata contributed by a plugin descriptor."""

    descriptor: AuthenticationProviderDescriptor
    config_schema: type[PluginConfigSchema] | None = None
    django_apps: tuple[str, ...] = ()
    url_modules: tuple[str, ...] = ()
    source_id_config_field: str | None = None
    supported_group_sync_modes: tuple[str, ...] = (
        "none",
        "additive",
        "exact",
    )

    def __post_init__(self) -> None:
        if self.config_schema is not None and not issubclass(
            self.config_schema, PluginConfigSchema
        ):
            raise TypeError("config_schema must inherit PluginConfigSchema")
        for value in (*self.django_apps, *self.url_modules):
            _require_non_empty(value, "authentication contribution module")
        if self.source_id_config_field is not None:
            _require_non_empty(self.source_id_config_field, "source id config field")
            if (
                self.config_schema is None
                or self.source_id_config_field not in self.config_schema.model_fields
            ):
                raise ValueError(
                    "source_id_config_field must name a config schema field"
                )
        allowed_group_sync_modes = {"none", "additive", "exact"}
        if (
            not self.supported_group_sync_modes
            or len(self.supported_group_sync_modes)
            != len(set(self.supported_group_sync_modes))
            or any(
                mode not in allowed_group_sync_modes
                for mode in self.supported_group_sync_modes
            )
        ):
            raise ValueError(
                "supported_group_sync_modes must be unique supported modes"
            )


class AttributeProvenance(StrEnum):
    VERIFIED_OWNERSHIP = "verified_ownership"
    AUTHORITY_MANAGED = "authority_managed"
    SELF_ASSERTED = "self_asserted"


@dataclass(frozen=True, slots=True)
class AssuredAttribute:
    value: str
    provenance: AttributeProvenance

    def __post_init__(self) -> None:
        _require_non_empty(self.value, "attribute value")
        if not isinstance(self.provenance, AttributeProvenance):
            raise TypeError(f"unsupported attribute provenance: {self.provenance!r}")


@dataclass(frozen=True, slots=True)
class ExternalProfile:
    """Normalized, non-authorizing profile values returned by a provider."""

    username: str | None = None
    display_name: str | None = None
    email: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("username", "display_name", "email"):
            value = getattr(self, field_name)
            if value is not None:
                _require_non_empty(value, f"profile {field_name}")


class ExternalGroupSnapshotStatus(StrEnum):
    UNSUPPORTED = "unsupported"
    COMPLETE = "complete"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class ExternalGroupSnapshot:
    """Completeness-aware external groups; complete-empty is authoritative."""

    status: ExternalGroupSnapshotStatus
    groups: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, ExternalGroupSnapshotStatus):
            raise TypeError(f"unsupported group snapshot status: {self.status!r}")
        if self.status is not ExternalGroupSnapshotStatus.COMPLETE and self.groups:
            raise ValueError("only a complete group snapshot may contain group values")
        for group in self.groups:
            _require_non_empty(group, "external group")
        if len(self.groups) != len(set(self.groups)):
            raise ValueError("external group values must be unique")

    @classmethod
    def unsupported(cls) -> ExternalGroupSnapshot:
        return cls(ExternalGroupSnapshotStatus.UNSUPPORTED)

    @classmethod
    def unavailable(cls) -> ExternalGroupSnapshot:
        return cls(ExternalGroupSnapshotStatus.UNAVAILABLE)

    @classmethod
    def complete(cls, groups: tuple[str, ...] = ()) -> ExternalGroupSnapshot:
        return cls(ExternalGroupSnapshotStatus.COMPLETE, groups)


@dataclass(frozen=True, slots=True)
class VerifiedIdentity:
    provider_id: AuthenticationProviderId
    source_id: str
    subject: str
    profile: ExternalProfile = field(default_factory=ExternalProfile)
    attributes: Mapping[str, AssuredAttribute] = field(default_factory=dict)
    groups: ExternalGroupSnapshot = field(
        default_factory=ExternalGroupSnapshot.unsupported
    )

    def __post_init__(self) -> None:
        _require_non_empty(self.provider_id, "verified identity provider id")
        _require_non_empty(self.source_id, "verified identity source id")
        _require_non_empty(self.subject, "verified identity subject")
        if not isinstance(self.profile, ExternalProfile):
            raise TypeError("profile must be ExternalProfile")
        if not isinstance(self.groups, ExternalGroupSnapshot):
            raise TypeError("groups must be ExternalGroupSnapshot")
        frozen = dict(self.attributes)
        for name, attribute in frozen.items():
            _require_non_empty(name, "attribute name")
            if not isinstance(attribute, AssuredAttribute):
                raise TypeError("identity attributes must be AssuredAttribute values")
        object.__setattr__(self, "attributes", MappingProxyType(frozen))

    def validate_for(self, *, provider_id: str, source_id: str) -> None:
        """Reject a result that escaped its configured provider/source boundary."""

        if self.provider_id != provider_id:
            raise InvalidAuthenticationResultError(
                f"expected provider_id={provider_id!r}, got {self.provider_id!r}"
            )
        if self.source_id != source_id:
            raise InvalidAuthenticationResultError(
                f"identity source does not match provider {provider_id!r}"
            )


class AuthenticationFailureCategory(StrEnum):
    INVALID_CREDENTIALS = "invalid_credentials"
    UNAVAILABLE = "unavailable"
    INVALID_RESULT = "invalid_result"
    CANCELED = "canceled"


@dataclass(frozen=True, slots=True)
class AuthenticationFailure:
    """Allowlisted failure data safe to cross the provider/Core boundary."""

    category: AuthenticationFailureCategory
    retryable: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.category, AuthenticationFailureCategory):
            raise TypeError(
                f"unsupported authentication failure category: {self.category!r}"
            )


@dataclass(frozen=True, slots=True)
class CredentialInput:
    """Ephemeral credential values with a deliberately redacted repr."""

    values: Mapping[str, str] = field(repr=False)

    def __post_init__(self) -> None:
        if not self.values:
            raise ValueError("credential input must not be empty")
        object.__setattr__(
            self,
            "values",
            _freeze_string_mapping(
                self.values,
                field_name="credential",
                allow_empty_values=False,
            ),
        )


@dataclass(frozen=True, slots=True)
class RedirectChallenge:
    """Provider authorization target; Core still validates its destination."""

    authorization_url: str = field(repr=False)

    def __post_init__(self) -> None:
        _require_non_empty(self.authorization_url, "authorization URL")


@dataclass(frozen=True, slots=True)
class AuthenticationFlowContext:
    provider_id: AuthenticationProviderId
    source_id: str
    attempt_id: str
    correlation_id: str
    deadline: datetime

    def __post_init__(self) -> None:
        _require_non_empty(self.provider_id, "context provider id")
        _require_non_empty(self.source_id, "context source id")
        _require_non_empty(self.attempt_id, "authentication attempt id")
        _require_non_empty(self.correlation_id, "authentication correlation id")
        if self.deadline.tzinfo is None or self.deadline.utcoffset() is None:
            raise ValueError("authentication deadline must be timezone-aware")


@dataclass(frozen=True, slots=True)
class CredentialFlowContext(AuthenticationFlowContext):
    pass


@dataclass(frozen=True, slots=True)
class RedirectFlowContext(AuthenticationFlowContext):
    callback_url: str

    def __post_init__(self) -> None:
        AuthenticationFlowContext.__post_init__(self)
        _require_non_empty(self.callback_url, "redirect callback URL")


@dataclass(frozen=True, slots=True)
class RedirectCallbackContext(AuthenticationFlowContext):
    callback_parameters: Mapping[str, str] = field(repr=False)
    callback_url: str | None = None

    def __post_init__(self) -> None:
        AuthenticationFlowContext.__post_init__(self)
        object.__setattr__(
            self,
            "callback_parameters",
            _freeze_string_mapping(
                self.callback_parameters,
                field_name="callback parameter",
                allow_empty_values=True,
            ),
        )
        if self.callback_url is not None:
            _require_non_empty(self.callback_url, "redirect callback URL")


@runtime_checkable
class CredentialAuthenticationProvider(Protocol):
    descriptor: AuthenticationProviderDescriptor

    def authenticate(
        self,
        context: CredentialFlowContext,
        credentials: CredentialInput,
    ) -> VerifiedIdentity | AuthenticationFailure: ...


@runtime_checkable
class RedirectAuthenticationProvider(Protocol):
    descriptor: AuthenticationProviderDescriptor

    def begin(self, context: RedirectFlowContext) -> RedirectChallenge: ...

    def complete(
        self, context: RedirectCallbackContext
    ) -> VerifiedIdentity | AuthenticationFailure: ...


type AuthenticationProvider = (
    CredentialAuthenticationProvider | RedirectAuthenticationProvider
)


class InvalidAuthenticationResultError(ValueError):
    """A provider returned an identity outside its registered boundary."""


class InvalidAuthenticationProviderError(TypeError):
    """A runtime provider does not implement its descriptor's flow protocol."""


class DuplicateAuthenticationProviderError(ValueError):
    def __init__(
        self,
        provider_id: str,
        *,
        existing_owner: str | None,
        new_owner: str | None,
    ) -> None:
        super().__init__(
            f"Authentication provider id={provider_id!r} is already registered "
            f"by {existing_owner!r}; conflicting registration from {new_owner!r}"
        )
        self.provider_id = provider_id
        self.existing_owner = existing_owner
        self.new_owner = new_owner


@runtime_checkable
class AuthenticationProviderLookup(Protocol):
    """Read-only provider discovery used by Authentication Core."""

    def get(self, provider_id: str) -> AuthenticationProvider | None: ...

    def all(self) -> tuple[AuthenticationProvider, ...]: ...

    def registered_ids(self) -> tuple[str, ...]: ...


class AuthenticationProviderRegistry:
    """Keyed runtime registry populated through the public register function."""

    def __init__(self) -> None:
        self._providers: dict[str, AuthenticationProvider] = {}
        self._owners: dict[str, str | None] = {}

    def register(
        self, provider: AuthenticationProvider, *, owner: str | None = None
    ) -> None:
        descriptor = provider.descriptor
        if not isinstance(descriptor, AuthenticationProviderDescriptor):
            raise InvalidAuthenticationProviderError(
                "provider descriptor must be AuthenticationProviderDescriptor"
            )
        provider_id = descriptor.id
        if provider_id in self._providers:
            raise DuplicateAuthenticationProviderError(
                provider_id,
                existing_owner=self._owners[provider_id],
                new_owner=owner,
            )
        if (
            descriptor.flow_kind is AuthenticationFlowKind.CREDENTIALS
            and not isinstance(provider, CredentialAuthenticationProvider)
        ) or (
            descriptor.flow_kind is AuthenticationFlowKind.REDIRECT
            and not isinstance(provider, RedirectAuthenticationProvider)
        ):
            raise InvalidAuthenticationProviderError(
                f"provider {provider_id!r} does not implement its declared "
                f"{descriptor.flow_kind.value!r} flow"
            )
        self._providers[provider_id] = provider
        self._owners[provider_id] = owner

    def get(self, provider_id: str) -> AuthenticationProvider | None:
        return self._providers.get(provider_id)

    def all(self) -> tuple[AuthenticationProvider, ...]:
        return tuple(self._providers.values())

    def registered_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._providers))


class _AuthenticationProviderReadView:
    __slots__ = ("__registry",)

    def __init__(self, registry: AuthenticationProviderRegistry) -> None:
        self.__registry = registry

    def get(self, provider_id: str) -> AuthenticationProvider | None:
        return self.__registry.get(provider_id)

    def all(self) -> tuple[AuthenticationProvider, ...]:
        return self.__registry.all()

    def registered_ids(self) -> tuple[str, ...]:
        return self.__registry.registered_ids()


_authentication_provider_registry = AuthenticationProviderRegistry()
_authentication_provider_lookup = _AuthenticationProviderReadView(
    _authentication_provider_registry
)


def register_authentication_provider(
    provider: AuthenticationProvider, *, owner: str | None = None
) -> None:
    """Register a runtime provider after Django setup."""

    _authentication_provider_registry.register(provider, owner=owner)


def get_authentication_provider_lookup() -> AuthenticationProviderLookup:
    """Return Core's read-only view of registered runtime providers."""

    return _authentication_provider_lookup
