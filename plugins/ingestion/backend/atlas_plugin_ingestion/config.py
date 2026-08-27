"""Typed configuration for `atlas.ingestion` — the `sources` list. Each source is
deployment-level connection/credential config for one git host, resolved
once at process startup via `resolve_secrets` and referenced by
`RegisteredRepository.source_id`; no ingestion credential is ever stored in
the database (sources are deployment-level configuration, not database rows).

Kept free of Django imports: `PLUGIN.config_schema` in `plugin.py` is
evaluated during the static plugin-descriptor phase, before `django.setup()`
runs (mirrors `atlas_plugin_auth_gitea.config`'s own Django-free shape).
"""

from typing import Literal
from urllib.parse import urlsplit

from atlas_plugin_api import FileRef, PluginConfigSchema, SecretRef
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .limits import (
    DEFAULT_MAX_FETCHED_FILE_BYTES,
    DEFAULT_MAX_INCLUDE_DEPTH,
    DEFAULT_MAX_INCLUDED_FILES,
    DEFAULT_MAX_YAML_NESTING_DEPTH,
)

_ALLOWED_SCHEMES = frozenset({"https", "http", "ssh"})
_HTTP_AUTH_KINDS = frozenset({"basic", "bearer"})


def _is_loopback_hostname(hostname: str | None) -> bool:
    return hostname in {"localhost", "127.0.0.1", "::1"} or bool(
        hostname and hostname.endswith(".localhost"),
    )


class SourceConfig(BaseModel):
    """One configured git host (a deployment-level entry in the `sources`
    plugin config"). `credential`'s shape depends on `auth_kind`
    (`connectors/git.py`'s `SourceConnection` docstring): `basic` ->
    `"<username>:<password>"`, `bearer` -> the raw token, `ssh-key` ->
    PEM-encoded private key content.

    `credential`/`known_hosts` are excluded from `repr` (`Field(repr=False)`)
    because, unlike a top-level `PluginConfigSchema` field, a field nested
    inside a `list[SourceConfig]` isn't covered by `PluginConfigSchema`'s own
    secret-redaction machinery (`_is_secret_capable` only inspects top-level
    field annotations) — this is this class's own guard against a resolved
    credential leaking into a log line or traceback.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        populate_by_name=True,
        hide_input_in_errors=True,
    )

    id: str = Field(min_length=1)
    base_url: str = Field(alias="baseUrl")
    auth_kind: Literal["basic", "bearer", "ssh-key"] = Field(alias="authKind")
    credential: str | SecretRef | FileRef = Field(repr=False)
    known_hosts: str | SecretRef | FileRef | None = Field(
        default=None,
        alias="knownHosts",
        repr=False,
    )
    accept_unknown_host_keys: bool = Field(
        default=False,
        alias="acceptUnknownHostKeys",
    )
    allow_development_http: bool = Field(
        default=False,
        alias="allowDevelopmentHttp",
    )

    @model_validator(mode="after")
    def _validate_base_url_and_auth_kind(self) -> "SourceConfig":
        """Validating `path` instead of the whole URL only works because
        `base_url`'s scheme/host is fixed and trustworthy at deploy time —
        enforced here, at config-validation time, not deferred to first
        clone)."""
        parsed = urlsplit(self.base_url)
        scheme = parsed.scheme.lower()
        if scheme not in _ALLOWED_SCHEMES:
            raise ValueError(
                f"source {self.id!r} baseUrl scheme {parsed.scheme!r} is not "
                f"supported; use one of {sorted(_ALLOWED_SCHEMES)}",
            )
        if scheme in ("https", "http"):
            if self.auth_kind not in _HTTP_AUTH_KINDS:
                raise ValueError(
                    f"source {self.id!r} authKind {self.auth_kind!r} is not "
                    "supported over http(s); use basic or bearer",
                )
            if scheme == "http" and not (
                self.allow_development_http and _is_loopback_hostname(parsed.hostname)
            ):
                raise ValueError(
                    f"source {self.id!r} baseUrl must use HTTPS outside "
                    "loopback development (set allowDevelopmentHttp to opt "
                    "in)",
                )
        elif self.auth_kind != "ssh-key":
            raise ValueError(
                f"source {self.id!r} authKind {self.auth_kind!r} is not "
                "supported over ssh; use ssh-key",
            )
        return self

    @model_validator(mode="after")
    def _require_host_key_verification_for_ssh(self) -> "SourceConfig":
        """Fail closed at composition/startup, not at the first scheduled
        clone (SSH host-key verification is fail-closed by default)."""
        if (
            self.auth_kind == "ssh-key"
            and self.known_hosts is None
            and not self.accept_unknown_host_keys
        ):
            raise ValueError(
                f"source {self.id!r} declares authKind 'ssh-key' but has "
                "neither knownHosts nor acceptUnknownHostKeys configured",
            )
        return self


class IngestionPluginConfig(PluginConfigSchema):
    """`atlas.ingestion` plugin configuration (deployment-level
    `sources` in plugin config"). Defaults to no sources so a deployment
    that hasn't configured any git host yet — or hasn't declared an
    `atlas.ingestion` config block at all — still composes cleanly; any
    `RegisteredRepository` referencing an unresolved `source_id` is reported
    as a clear per-repository error at ingestion time, not a startup
    failure.

    The `max*` fields bound a single fetch/parse operation (`limits.py`'s
    `IngestionLimits`, resolved at ingestion time via `limits.
    resolved_limits()`) — operator-configurable rather than hardcoded, so a
    deployment with legitimately larger manifests/SQL files isn't stuck
    """

    sources: list[SourceConfig] = Field(default_factory=list)
    max_fetched_file_bytes: int = Field(
        default=DEFAULT_MAX_FETCHED_FILE_BYTES,
        alias="maxFetchedFileBytes",
        gt=0,
    )
    max_yaml_nesting_depth: int = Field(
        default=DEFAULT_MAX_YAML_NESTING_DEPTH,
        alias="maxYamlNestingDepth",
        gt=0,
    )
    max_include_depth: int = Field(
        default=DEFAULT_MAX_INCLUDE_DEPTH,
        alias="maxIncludeDepth",
        gt=0,
    )
    max_included_files: int = Field(
        default=DEFAULT_MAX_INCLUDED_FILES,
        alias="maxIncludedFiles",
        gt=0,
    )
