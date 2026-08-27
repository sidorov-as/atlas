"""Manifest -> lock resolution.

Resolves each manifest-declared plugin's exact artifact version and
integrity by cross-referencing this monorepo's own native lock files
(`poetry.lock` for backend, the root `package-lock.json` for frontend)
rather than re-deriving hashes independently. Only
the `workspace` artifact source is resolvable this way; the other sources
`manifest.ArtifactSource` accepts name real package registries this
composer doesn't fetch from yet.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path

from atlas_plugin_api import PluginDescriptor

from .auth import authentication_provider_contributions
from .generate import backend_module_path
from .lock import (
    Lock,
    LockedAuthConfig,
    LockedAuthProvider,
    LockedBackendArtifact,
    LockedCredentialField,
    LockedFrontendArtifact,
    LockedPlugin,
    LockedProviderPresentation,
)
from .manifest import Manifest, PluginArtifact
from .npm_lock import ResolvedFrontendPackage, parse_npm_lock
from .poetry_lock import ResolvedPythonPackage, parse_poetry_lock


class ResolutionError(Exception):
    """Raised when a manifest can't be resolved to a lock."""


class UnknownPackageError(ResolutionError):
    def __init__(self, package: str, lock_kind: str) -> None:
        super().__init__(f"{package!r} not found in {lock_kind}")
        self.package = package


class VersionMismatchError(ResolutionError):
    def __init__(
        self,
        plugin_id: str,
        manifest_version: str,
        resolved_version: str,
    ) -> None:
        super().__init__(
            f"{plugin_id!r} declares version {manifest_version!r} in the "
            f"manifest, but {resolved_version!r} is resolved from the "
            "native lock",
        )
        self.plugin_id = plugin_id


class UnsupportedSourceError(ResolutionError):
    def __init__(self, package: str, source: str) -> None:
        super().__init__(
            f"{package!r} declares source {source!r}, which this composer "
            "cannot resolve yet (only 'workspace' is implemented)",
        )
        self.package = package
        self.source = source


@dataclass(frozen=True, slots=True)
class NativeLocks:
    """The native lock files the resolver cross-references, each keyed by
    package name."""

    python: dict[str, ResolvedPythonPackage]
    npm: dict[str, ResolvedFrontendPackage]

    @classmethod
    def from_repo_root(cls, repo_root: Path) -> "NativeLocks":
        return cls(
            python=parse_poetry_lock(
                repo_root / "core" / "backend" / "poetry.lock",
            ),
            npm=parse_npm_lock(repo_root / "package-lock.json"),
        )


def _resolve_backend(
    plugin_id: str,
    version: str,
    artifact: PluginArtifact,
    locks: NativeLocks,
) -> LockedBackendArtifact:
    if artifact.source != "workspace":
        raise UnsupportedSourceError(artifact.package, artifact.source)
    resolved = locks.python.get(artifact.package)
    if resolved is None:
        raise UnknownPackageError(artifact.package, "poetry.lock")
    if resolved.version != version:
        raise VersionMismatchError(plugin_id, version, resolved.version)
    return LockedBackendArtifact(
        package=artifact.package,
        version=resolved.version,
        hash=resolved.hash,
    )


def _resolve_frontend(
    plugin_id: str,
    version: str,
    artifact: PluginArtifact,
    locks: NativeLocks,
) -> LockedFrontendArtifact:
    if artifact.source != "workspace":
        raise UnsupportedSourceError(artifact.package, artifact.source)
    resolved = locks.npm.get(artifact.package)
    if resolved is None:
        raise UnknownPackageError(artifact.package, "package-lock.json")
    if resolved.version != version:
        raise VersionMismatchError(plugin_id, version, resolved.version)
    return LockedFrontendArtifact(
        package=artifact.package,
        version=resolved.version,
        integrity=resolved.integrity,
    )


def _load_resolved_descriptors(
    plugins: Mapping[str, LockedPlugin],
) -> dict[str, PluginDescriptor]:
    descriptors = {}
    for key, plugin in plugins.items():
        if plugin.backend is None or plugin.disabled:
            continue
        plugin_id = key.rsplit("@", 1)[0]
        module = import_module(backend_module_path(plugin.backend.package))
        descriptors[plugin_id] = module.PLUGIN
    return descriptors


def _resolve_auth(
    manifest: Manifest,
    descriptors: Mapping[str, PluginDescriptor],
) -> LockedAuthConfig:
    contributions = authentication_provider_contributions(descriptors)
    providers = []
    for selected in manifest.auth.providers:
        contribution_entry = contributions.get(selected.id)
        if contribution_entry is None:
            # Composition validation owns the actionable error. Preserve enough
            # policy in no lock entry rather than inventing provider metadata.
            continue
        owner, contribution = contribution_entry
        descriptor = contribution.descriptor
        presentation = descriptor.presentation
        providers.append(
            LockedAuthProvider(
                **selected.model_dump(by_alias=True),
                owner=owner,
                contractVersion=descriptor.contract_version,
                flowKind=descriptor.flow_kind.value,
                remoteLogout=descriptor.remote_logout.value,
                presentation=LockedProviderPresentation(
                    displayName=presentation.display_name,
                    credentialFields=tuple(
                        LockedCredentialField(
                            id=field.id,
                            label=field.label,
                            kind=field.kind.value,
                            autocomplete=field.autocomplete,
                        )
                        for field in presentation.credential_fields
                    ),
                ),
            )
        )
    return LockedAuthConfig(
        providers=tuple(providers),
        default=manifest.auth.default,
        sessionMaxAgeSeconds=manifest.auth.session_max_age_seconds,
        publicOrigin=manifest.auth.public_origin,
        trustedProxyAddresses=manifest.auth.trusted_proxy_addresses,
        adminPassword=manifest.auth.admin_password,
        outboundTrust=manifest.auth.outbound_trust,
        passwordPolicy=manifest.auth.password_policy,
        recovery=manifest.auth.recovery,
    )


def resolve_manifest(
    manifest: Manifest,
    *,
    repo_root: Path,
    descriptors: Mapping[str, PluginDescriptor] | None = None,
) -> Lock:
    """Resolve `manifest` to a `Lock`, using `repo_root`'s native lock files
    for every `workspace`-sourced plugin artifact."""
    locks = NativeLocks.from_repo_root(repo_root)
    plugins: dict[str, LockedPlugin] = {}
    for entry in manifest.plugins:
        backend = None
        if entry.backend is not None:
            backend = _resolve_backend(
                entry.id,
                entry.version,
                entry.backend,
                locks,
            )
        frontend = None
        if entry.frontend is not None:
            frontend = _resolve_frontend(
                entry.id,
                entry.version,
                entry.frontend,
                locks,
            )
        plugins[f"{entry.id}@{entry.version}"] = LockedPlugin(
            backend=backend,
            frontend=frontend,
            disabled=entry.disabled,
            config=entry.config,
        )

    needs_plugin_descriptors = any(
        provider.id != "atlas.auth.local" for provider in manifest.auth.providers
    )
    if descriptors is None and needs_plugin_descriptors:
        descriptors = _load_resolved_descriptors(plugins)

    return Lock(
        distribution=f"{manifest.distribution.id}@{manifest.distribution.version}",
        core=manifest.core.version,
        plugins=plugins,
        auth=_resolve_auth(manifest, descriptors or {}),
    )
