"""Deployment manifest schema.

An operator declares plugin selection, versions, and artifact sources in a
source-controlled YAML manifest (`docs/plugin-architecture.md:493-525`).
`resolver.resolve_manifest` turns a `Manifest` into a `lock.Lock`.
"""

import ipaddress
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ArtifactSource = Literal[
    "workspace",
    "python-private",
    "npm-private",
    "pypi",
    "npm",
]
"""Where the composer resolves a plugin artifact from. `workspace` resolves
against this monorepo's own native lock files (`poetry.lock`,
`package-lock.json`) — the only source `resolver.py` currently implements.
The registry sources match `docs/plugin-architecture.md:511-524`'s
illustrative manifest and are accepted by the schema for forward
compatibility; resolving them raises `resolver.UnsupportedSourceError`."""


class _Base(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        populate_by_name=True,
    )


class DistributionInfo(_Base):
    id: str
    version: str


class CoreInfo(_Base):
    version: str


class PluginArtifact(_Base):
    package: str
    source: ArtifactSource


class PluginEntry(_Base):
    id: str
    version: str
    backend: PluginArtifact | None = None
    frontend: PluginArtifact | None = None
    disabled: bool = False
    """Plugin-lifecycle state: `False` (the
    default) is the `active` state — the plugin's contributions register
    normally. `True` is `disabled` — the plugin's code still installs (so
    its Django app loads and its migrations still apply) but its
    contribution/registration loading is skipped and any background jobs
    it registered are paused, without touching its data. Distinct from
    simply omitting the entry (`removed`), which this schema doesn't
    represent at all."""

    config: dict[str, Any] = Field(default_factory=dict)
    """Raw, not-yet-schema-validated configuration
    (`docs/plugin-architecture.md:475-491`), e.g. `{'issuer': '...',
    'clientSecret': {'fromEnv': 'ATLAS_OIDC_CLIENT_SECRET'}}`.
    `atlas_composer.composition.check_plugin_config` validates this against
    the plugin's own `PluginDescriptor.config_schema`; kept untyped here
    since the manifest schema itself has no per-plugin knowledge of what a
    valid shape is."""

    @model_validator(mode="after")
    def _require_an_artifact(self) -> "PluginEntry":
        # A plugin may be backend-only or frontend-only
        # (`docs/plugin-architecture.md:219`), but not neither.
        if self.backend is None and self.frontend is None:
            msg = (
                f"plugin {self.id!r} declares neither a backend nor a frontend artifact"
            )
            raise ValueError(msg)
        return self


class RestrictedAttributeRequirement(_Base):
    name: str
    accepted_provenance: tuple[
        Literal["verified-ownership", "authority-managed"], ...
    ] = Field(alias="acceptedProvenance")


class GroupSyncConfig(_Base):
    mode: Literal["none", "additive", "exact"] = "none"
    snapshot_requirement: Literal[
        "unsupported",
        "best-effort",
        "required",
    ] = Field(default="unsupported", alias="snapshotRequirement")
    max_age_seconds: int = Field(default=28800, gt=0, alias="maxAgeSeconds")
    mappings: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _default_snapshot_requirement(cls, data: Any) -> Any:
        if isinstance(data, dict) and "snapshotRequirement" not in data:
            data = dict(data)
            if data.get("mode") == "exact":
                data["snapshotRequirement"] = "required"
            elif data.get("mode") == "additive":
                data["snapshotRequirement"] = "best-effort"
        return data

    @model_validator(mode="after")
    def _validate_mode(self) -> "GroupSyncConfig":
        if self.mode == "none" and self.mappings:
            raise ValueError("groupSync mappings require additive or exact mode")
        expected = {
            "none": {"unsupported"},
            "additive": {"best-effort", "required"},
            "exact": {"required"},
        }[self.mode]
        if self.snapshot_requirement not in expected:
            raise ValueError(
                f"groupSync mode {self.mode!r} does not support "
                f"snapshotRequirement={self.snapshot_requirement!r}",
            )
        return self


class SourceBindingConfig(_Base):
    source_id: str = Field(alias="sourceId", min_length=1)
    configuration_fingerprint: str = Field(
        alias="configurationFingerprint",
        min_length=1,
    )


class AuthProviderEntry(_Base):
    id: str = Field(min_length=1)
    signup: Literal["disabled", "enabled"] = "disabled"
    principal_provisioning: Literal[
        "preprovisioned",
        "automatic",
        "restricted",
    ] = Field(default="preprovisioned", alias="principalProvisioning")
    actor_provisioning: Literal["manual", "automatic"] = Field(
        default="manual",
        alias="actorProvisioning",
    )
    profile_fields: tuple[Literal["username", "displayName", "email"], ...] = Field(
        default=(), alias="profileFields"
    )
    group_sync: GroupSyncConfig = Field(
        default_factory=GroupSyncConfig,
        alias="groupSync",
    )
    restricted_attributes: tuple[RestrictedAttributeRequirement, ...] = Field(
        default=(),
        alias="restrictedAttributes",
    )
    source_binding: SourceBindingConfig | None = Field(
        default=None,
        alias="sourceBinding",
    )

    @model_validator(mode="after")
    def _validate_policy(self) -> "AuthProviderEntry":
        if self.id != "atlas.auth.local" and self.signup != "disabled":
            raise ValueError("signup may be enabled only for atlas.auth.local")
        if self.principal_provisioning == "restricted":
            if not self.restricted_attributes:
                raise ValueError(
                    "restricted principal provisioning requires restrictedAttributes",
                )
        elif self.restricted_attributes:
            raise ValueError(
                "restrictedAttributes require principalProvisioning=restricted",
            )
        if len(self.profile_fields) != len(set(self.profile_fields)):
            raise ValueError("profileFields must be unique")
        return self


class AdminPasswordConfig(_Base):
    mode: Literal["disabled", "break-glass"] = "disabled"
    principal_ids: tuple[int, ...] = Field(
        default=(),
        alias="principalIds",
    )

    @field_validator("principal_ids")
    @classmethod
    def _positive_unique_ids(cls, values: tuple[int, ...]) -> tuple[int, ...]:
        if any(value <= 0 for value in values):
            raise ValueError("admin password Principal ids must be positive")
        if len(values) != len(set(values)):
            raise ValueError("admin password Principal ids must be unique")
        return values

    @model_validator(mode="after")
    def _require_allowlist(self) -> "AdminPasswordConfig":
        if self.mode == "break-glass" and not self.principal_ids:
            raise ValueError(
                "break-glass admin password login requires principalIds",
            )
        if self.mode == "disabled" and self.principal_ids:
            raise ValueError("principalIds require mode=break-glass")
        return self


class OutboundTrustConfig(_Base):
    allowed_destinations: tuple[str, ...] = Field(
        default=(),
        alias="allowedDestinations",
    )
    allow_development_http: bool = Field(
        default=False,
        alias="allowDevelopmentHttp",
    )

    @field_validator("allowed_destinations")
    @classmethod
    def _validate_destinations(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        for value in values:
            parsed = urlsplit(value)
            if parsed.scheme not in {"https", "http"} or not parsed.hostname:
                raise ValueError(
                    "allowed destinations must be absolute HTTP(S) origins",
                )
            if parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise ValueError("allowed destinations must be credential-free origins")
            if parsed.scheme == "http" and not cls._is_loopback(parsed.hostname):
                raise ValueError(
                    "plaintext destinations are allowed only for loopback fixtures",
                )
        if len(values) != len(set(values)):
            raise ValueError("allowed destinations must be unique")
        return values

    @staticmethod
    def _is_loopback(hostname: str) -> bool:
        return hostname in {"localhost", "127.0.0.1", "::1"} or hostname.endswith(
            ".localhost"
        )

    @model_validator(mode="after")
    def _require_development_opt_in(self) -> "OutboundTrustConfig":
        has_http = any(
            value.startswith("http://") for value in self.allowed_destinations
        )
        if has_http and not self.allow_development_http:
            raise ValueError(
                "loopback HTTP destinations require allowDevelopmentHttp=true",
            )
        return self


class PasswordPolicyConfig(_Base):
    minimum_length: int = Field(default=15, ge=15, alias="minimumLength")
    maximum_length: int = Field(default=128, ge=64, alias="maximumLength")
    reject_common: bool = Field(default=True, alias="rejectCommon")
    reject_user_similarity: bool = Field(
        default=True,
        alias="rejectUserSimilarity",
    )

    @model_validator(mode="after")
    def _validate_lengths(self) -> "PasswordPolicyConfig":
        if self.maximum_length < self.minimum_length:
            raise ValueError("maximumLength must be at least minimumLength")
        return self


class RecoveryPolicyConfig(_Base):
    mode: Literal["operator-managed", "public"] = "operator-managed"
    verified_addresses_required: bool = Field(
        default=True,
        alias="verifiedAddressesRequired",
    )
    token_max_age_seconds: int = Field(
        default=3600,
        gt=0,
        alias="tokenMaxAgeSeconds",
    )


class AuthConfig(_Base):
    providers: tuple[AuthProviderEntry, ...] = ()
    default: str | None = None
    session_max_age_seconds: int = Field(
        default=28800,
        gt=0,
        alias="sessionMaxAgeSeconds",
    )
    public_origin: str | None = Field(default=None, alias="publicOrigin")
    trusted_proxy_addresses: tuple[str, ...] = Field(
        default=(),
        alias="trustedProxyAddresses",
    )
    admin_password: AdminPasswordConfig = Field(
        default_factory=AdminPasswordConfig,
        alias="adminPassword",
    )
    outbound_trust: OutboundTrustConfig = Field(
        default_factory=OutboundTrustConfig,
        alias="outboundTrust",
    )
    password_policy: PasswordPolicyConfig = Field(
        default_factory=PasswordPolicyConfig,
        alias="passwordPolicy",
    )
    recovery: RecoveryPolicyConfig = Field(
        default_factory=RecoveryPolicyConfig,
    )

    @model_validator(mode="before")
    @classmethod
    def _reject_legacy_provider_strings(cls, data: Any) -> Any:
        if isinstance(data, dict):
            providers = data.get("providers", ())
            if any(isinstance(provider, str) for provider in providers):
                raise ValueError(
                    "legacy auth.providers string entries are no longer "
                    "supported; replace each id with an object such as "
                    "{id: atlas.auth.local, signup: disabled, "
                    "principalProvisioning: preprovisioned, "
                    "actorProvisioning: manual}",
                )
        return data

    @field_validator("public_origin")
    @classmethod
    def _validate_public_origin(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = urlsplit(value)
        if parsed.scheme not in {"https", "http"} or not parsed.hostname:
            raise ValueError("publicOrigin must be an absolute HTTP(S) origin")
        if (
            parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
        ):
            raise ValueError("publicOrigin must contain only scheme and authority")
        if parsed.scheme == "http" and parsed.hostname not in {
            "localhost",
            "127.0.0.1",
            "::1",
        }:
            raise ValueError("publicOrigin must use HTTPS outside development")
        return value.rstrip("/")

    @field_validator("trusted_proxy_addresses")
    @classmethod
    def _validate_trusted_proxy_addresses(
        cls,
        values: tuple[str, ...],
    ) -> tuple[str, ...]:
        for value in values:
            try:
                ipaddress.ip_address(value)
            except ValueError as error:
                raise ValueError(
                    "trustedProxyAddresses entries must be IP addresses",
                ) from error
        if len(values) != len(set(values)):
            raise ValueError("trustedProxyAddresses must be unique")
        return values


class UiConfig(_Base):
    disable: tuple[str, ...] = ()
    order: tuple[str, ...] = ()


class Manifest(_Base):
    distribution: DistributionInfo
    core: CoreInfo
    plugins: tuple[PluginEntry, ...] = ()
    auth: AuthConfig = Field(default_factory=AuthConfig)
    ui: UiConfig = Field(default_factory=UiConfig)


def load_manifest(path: Path) -> Manifest:
    """Parse a deployment manifest YAML file into a validated `Manifest`."""
    with open(path) as manifest_file:
        data = yaml.safe_load(manifest_file)
    return Manifest.model_validate(data)
