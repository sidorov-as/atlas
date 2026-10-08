"""Distribution lock file schema.

Records exact resolved versions for every selected plugin
(`docs/plugin-architecture.md:527-545`) — `resolver.resolve_manifest`'s
output. Integrity of installed artifacts is not recorded here: it comes from
the native `uv.lock` and `package-lock.json`, which `uv sync --frozen` and
`npm ci` verify (reusing each ecosystem's native lock mechanism rather
than inventing a third custom lock format).
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from .manifest import (
    AdminPasswordConfig,
    GroupSyncConfig,
    OutboundTrustConfig,
    PasswordPolicyConfig,
    RecoveryPolicyConfig,
    RestrictedAttributeRequirement,
    SourceBindingConfig,
)


class _Base(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        populate_by_name=True,
    )


class LockedBackendArtifact(_Base):
    package: str
    version: str


class LockedFrontendArtifact(_Base):
    package: str
    version: str


class LockedPlugin(_Base):
    backend: LockedBackendArtifact | None = None
    frontend: LockedFrontendArtifact | None = None
    disabled: bool = False
    """Carried over from the manifest's `PluginEntry.disabled` so generation can see it without re-reading the manifest."""
    config: dict[str, Any] = Field(default_factory=dict, repr=False)
    """Validated unresolved plugin configuration; secrets remain references."""


class LockedService(_Base):
    """One required service as the lock pins it. Holds the secret's
    environment variable *name* only, never a value."""

    plugin: str
    id: str
    image: str
    port: int
    health_check: tuple[str, ...] = Field(alias="healthCheck")
    address_key: str = Field(alias="addressKey")
    secret_key: str | None = Field(default=None, alias="secretKey")
    secret_env: str | None = Field(default=None, alias="secretEnv")
    """Environment variable the container reads its key from."""
    secret_from_env: str | None = Field(default=None, alias="secretFromEnv")
    """Environment variable the operator sets; the plugin config references it
    as `{fromEnv: ...}`."""
    data_path: str | None = Field(default=None, alias="dataPath")
    external: bool = False
    address: str | None = None


class LockedCredentialField(_Base):
    id: str
    label: str
    kind: str
    autocomplete: str | None = None


class LockedProviderPresentation(_Base):
    display_name: str = Field(alias="displayName")
    credential_fields: tuple[LockedCredentialField, ...] = Field(
        default=(),
        alias="credentialFields",
    )


class LockedAuthProvider(_Base):
    id: str
    owner: str
    contract_version: str = Field(alias="contractVersion")
    flow_kind: str = Field(alias="flowKind")
    remote_logout: str = Field(alias="remoteLogout")
    presentation: LockedProviderPresentation
    signup: str = "disabled"
    principal_provisioning: str = Field(alias="principalProvisioning")
    actor_provisioning: str = Field(alias="actorProvisioning")
    profile_fields: tuple[str, ...] = Field(alias="profileFields")
    group_sync: GroupSyncConfig = Field(alias="groupSync")
    restricted_attributes: tuple[RestrictedAttributeRequirement, ...] = Field(
        default=(),
        alias="restrictedAttributes",
    )
    source_binding: SourceBindingConfig | None = Field(
        default=None,
        alias="sourceBinding",
    )


class LockedAuthConfig(_Base):
    providers: tuple[LockedAuthProvider, ...] = ()
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


class Lock(_Base):
    distribution: str
    """`{distribution.id}@{distribution.version}`, e.g.
    `company.atlas@2026.08`."""

    core: str
    plugins: dict[str, LockedPlugin]
    """Keyed by `{plugin.id}@{plugin.version}`, e.g. `atlas.apis@1.4.2`."""

    auth: LockedAuthConfig = Field(default_factory=LockedAuthConfig)

    services: dict[str, LockedService] = Field(default_factory=dict)
    """Keyed by `{plugin.id}/{service.id}`; empty when no selected plugin
    declares a service, which keeps such a lock byte-identical to before."""


def load_lock(path: Path) -> Lock:
    """Parse a lock file YAML document into a validated `Lock`."""
    with open(path) as lock_file:
        data = yaml.safe_load(lock_file)
    if _has_legacy_integrity_fields(data):
        raise ValueError(
            f"{path} still records `hash` or `integrity` values, which the lock "
            "no longer carries; re-resolve it from the manifest (`make lock`)",
        )
    return Lock.model_validate(data)


def _has_legacy_integrity_fields(data: Any) -> bool:
    plugins = data.get("plugins") if isinstance(data, dict) else None
    if not isinstance(plugins, dict):
        return False
    for plugin in plugins.values():
        if not isinstance(plugin, dict):
            continue
        for side, field in (("backend", "hash"), ("frontend", "integrity")):
            artifact = plugin.get(side)
            if isinstance(artifact, dict) and field in artifact:
                return True
    return False


def dump_lock(lock: Lock, path: Path) -> None:
    """Write `lock` to `path` as YAML, in the schema's declared field order."""
    document = lock.model_dump(exclude_defaults=True, by_alias=True)
    # Authentication policy defaults are security behavior, not cosmetic
    # schema defaults. Preserve them explicitly so a lock is self-contained
    # and reviewable even when the manifest relied on conservative defaults.
    document["auth"] = lock.auth.model_dump(by_alias=True, exclude_none=True)
    with open(path, "w") as lock_file:
        yaml.safe_dump(
            document,
            lock_file,
            sort_keys=False,
        )
