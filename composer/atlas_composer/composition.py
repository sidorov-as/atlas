"""Static composition validation.

Runs purely from a `Manifest`, its resolved `Lock`, and each selected
backend plugin's already-imported `PluginDescriptor`
(`descriptors.load_backend_descriptors`) — everything decidable before
`django.setup()` or a frontend build even starts (backend/frontend
version consistency, Core compatibility ranges, manifest dependency
presence, dependency cycles, duplicate manifest plugin ids). Static
checks run first so a manifest that's already invalid fails fast, without
attempting either build.

This module is layered *underneath* the runtime validators that were
already there: `server.apps.plugins.composition.
validate_composition` (duplicate Entity Kind/Capability/Permission id,
run from Django's `AppConfig.ready()`) and `compose.ts`'s
`composeFrontendPlugins` (duplicate contribution id, reserved/conflicting
route path, run when the frontend module graph loads) — both stay the
last line of defense for anything only detectable once code actually
runs. The generation step is what makes those runtime checks see
the *full* manifest-declared plugin set, so their
existing "Duplicate contribution id across two plugins fails the build"
coverage doesn't need a Python-side re-implementation here.

One more rule isn't this module's
job: "A forbidden import edge fails CI" is the CI import-boundary check
(added in CI), not something the composer decides at build time.

"Invalid plugin configuration fails the build" *is* this module's job
(`check_plugin_config`), now that `atlas_plugin_api.config.PluginConfigSchema`
gives every plugin a schema to validate a manifest entry's
`config` block against — structurally only: a `fromEnv` secret reference is
valid shape, never resolved here (`atlas_plugin_api.config.resolve_secrets`
is Core's job, at deploy time, not the composer's, at build time).
"""

from collections.abc import Mapping

from atlas_plugin_api import PluginDescriptor
from pydantic import ValidationError

from .auth import LOCAL_AUTHENTICATION_PROVIDER, LOCAL_PROVIDER_ID
from .lock import Lock
from .manifest import Manifest
from .semver import range_contains
from .services import resolve_required_services, wire_plugin_config

SEARCH_PLUGIN_ID = "atlas.search"


class CompositionError(Exception):
    """Raised when a static composition-validation check fails."""


class DuplicatePluginIdError(CompositionError):
    def __init__(self, plugin_id: str) -> None:
        super().__init__(
            f"Manifest declares plugin id {plugin_id!r} more than once",
        )
        self.plugin_id = plugin_id


class ArtifactVersionMismatchError(CompositionError):
    def __init__(
        self,
        key: str,
        backend_version: str,
        frontend_version: str,
    ) -> None:
        super().__init__(
            f"{key!r} locks mismatched backend ({backend_version!r}) and "
            f"frontend ({frontend_version!r}) artifact versions for the "
            "same logical plugin",
        )
        self.key = key
        self.backend_version = backend_version
        self.frontend_version = frontend_version


class IncompatibleCoreRangeError(CompositionError):
    def __init__(
        self,
        plugin_id: str,
        core_version: str,
        required_range: str,
    ) -> None:
        super().__init__(
            f"{plugin_id!r} requires atlasCore {required_range!r}, "
            f"incompatible with core version {core_version!r}",
        )
        self.plugin_id = plugin_id
        self.core_version = core_version
        self.required_range = required_range


class MissingDependencyError(CompositionError):
    def __init__(self, plugin_id: str, missing: frozenset[str]) -> None:
        super().__init__(
            f"{plugin_id!r} requires plugin(s) missing from the manifest: "
            f"{', '.join(sorted(missing))}",
        )
        self.plugin_id = plugin_id
        self.missing = missing


class DependencyCycleError(CompositionError):
    def __init__(self, cycle: tuple[str, ...]) -> None:
        super().__init__(
            f"Manifest plugin dependencies form a cycle: {' -> '.join(cycle)}",
        )
        self.cycle = cycle


class InvalidPluginConfigError(CompositionError):
    def __init__(self, plugin_id: str, error: str) -> None:
        super().__init__(
            f"{plugin_id!r} has invalid configuration: {error}",
        )
        self.plugin_id = plugin_id


class InvalidRequiredServiceError(CompositionError):
    """A declared or configured required service cannot be composed."""


class ConflictingServiceError(InvalidRequiredServiceError):
    def __init__(self, service_id: str, first: str, second: str, field: str) -> None:
        super().__init__(
            f"Service {service_id!r} is declared by {first!r} and {second!r} "
            f"with conflicting {field}",
        )
        self.service_id = service_id
        self.plugins = (first, second)


class InvalidSearchEngineSelectionError(CompositionError):
    def __init__(self, engine_plugin_id: str, reason: str) -> None:
        super().__init__(
            f"{SEARCH_PLUGIN_ID!r} setting 'engine' names {engine_plugin_id!r}, "
            f"but {reason}",
        )
        self.engine_plugin_id = engine_plugin_id


class InvalidAuthenticationSelectionError(CompositionError):
    """The authoritative auth selection cannot be activated safely."""


def _auth_error(message: str) -> InvalidAuthenticationSelectionError:
    return InvalidAuthenticationSelectionError(
        f"Invalid auth configuration: {message}. Define a non-empty auth block "
        "with policy-bearing providers, for example: "
        "auth: {providers: [{id: atlas.auth.local, signup: disabled, "
        "principalProvisioning: preprovisioned, actorProvisioning: manual}], "
        "default: atlas.auth.local}",
    )


def authentication_configuration_diff(
    manifest: Manifest,
    lock: Lock,
) -> tuple[str, ...]:
    """Actionable auth-only manifest/lock differences for reviews and CI."""

    selected_ids = [provider.id for provider in manifest.auth.providers]
    locked_ids = [provider.id for provider in lock.auth.providers]
    messages = []
    if not selected_ids:
        messages.append(
            "auth.providers is empty; add policy-bearing provider entries "
            "(for local-only: {id: atlas.auth.local, signup: disabled, "
            "principalProvisioning: preprovisioned, actorProvisioning: manual})",
        )
    duplicates = sorted({item for item in selected_ids if selected_ids.count(item) > 1})
    if duplicates:
        messages.append(f"duplicate auth provider ids: {', '.join(duplicates)}")
    if manifest.auth.default not in selected_ids:
        messages.append(
            f"auth.default {manifest.auth.default!r} is not in selected providers",
        )
    if selected_ids != locked_ids:
        messages.append(
            f"auth provider order differs: manifest={selected_ids!r}, "
            f"lock={locked_ids!r}; rerun atlas-compose resolve",
        )
    if manifest.auth.default != lock.auth.default:
        messages.append(
            f"auth default differs: manifest={manifest.auth.default!r}, "
            f"lock={lock.auth.default!r}; rerun atlas-compose resolve",
        )
    return tuple(messages)


def check_authentication_selection(
    manifest: Manifest,
    lock: Lock,
    descriptors: Mapping[str, PluginDescriptor],
) -> None:
    selected = manifest.auth.providers
    if not selected:
        raise _auth_error("auth.providers must select at least one provider")

    selected_ids = [provider.id for provider in selected]
    duplicate_ids = sorted(
        {item for item in selected_ids if selected_ids.count(item) > 1}
    )
    if duplicate_ids:
        raise _auth_error(
            f"duplicate provider ids are not allowed: {', '.join(duplicate_ids)}",
        )
    if manifest.auth.default is None:
        raise _auth_error("auth.default is required")
    if manifest.auth.default not in selected_ids:
        raise _auth_error(
            f"default provider {manifest.auth.default!r} is not selected",
        )

    contributions = {
        LOCAL_PROVIDER_ID: ("atlas.catalog", LOCAL_AUTHENTICATION_PROVIDER),
    }
    owners: dict[str, list[str]] = {LOCAL_PROVIDER_ID: ["atlas.catalog"]}
    for owner, descriptor in descriptors.items():
        for contribution in descriptor.authentication_providers:
            provider_id = contribution.descriptor.id
            owners.setdefault(provider_id, []).append(owner)
            contributions[provider_id] = (owner, contribution)

    manifest_plugins = {entry.id: entry for entry in manifest.plugins}
    for provider in selected:
        if provider.id != LOCAL_PROVIDER_ID:
            provider_owners = owners.get(provider.id, [])
            if not provider_owners:
                raise _auth_error(
                    f"selected provider {provider.id!r} has no declared descriptor "
                    "or owning plugin artifact",
                )
            if len(provider_owners) > 1:
                raise _auth_error(
                    f"provider {provider.id!r} is declared by multiple owners: "
                    f"{', '.join(sorted(provider_owners))}",
                )
            owner = provider_owners[0]
            plugin = manifest_plugins.get(owner)
            if plugin is None or plugin.backend is None:
                raise _auth_error(
                    f"provider {provider.id!r} requires backend artifact for "
                    f"owning plugin {owner!r}",
                )
            if plugin.disabled:
                raise _auth_error(
                    f"provider {provider.id!r} belongs to disabled plugin {owner!r}",
                )
        contribution = contributions[provider.id][1]
        if contribution.source_id_config_field is not None:
            owner = contributions[provider.id][0]
            plugin = manifest_plugins[owner]
            config_schema = contribution.config_schema
            if config_schema is None:
                raise _auth_error(
                    f"provider {provider.id!r} declares a source field "
                    "without a configuration schema",
                )
            typed_config = config_schema.model_validate(plugin.config)
            expected_source_id = getattr(
                typed_config,
                contribution.source_id_config_field,
            )
            if provider.source_binding is None:
                raise _auth_error(
                    f"provider {provider.id!r} requires sourceBinding.sourceId="
                    f"{expected_source_id!r}",
                )
            if provider.source_binding.source_id != expected_source_id:
                raise _auth_error(
                    f"provider {provider.id!r} sourceBinding.sourceId must "
                    f"match configured {contribution.source_id_config_field} "
                    f"{expected_source_id!r}",
                )
        if provider.group_sync.mode not in contribution.supported_group_sync_modes:
            supported = ", ".join(contribution.supported_group_sync_modes)
            raise _auth_error(
                f"provider {provider.id!r} does not support "
                f"groupSync.mode={provider.group_sync.mode!r}; supported: "
                f"{supported}",
            )

    locked_ids = [provider.id for provider in lock.auth.providers]
    if locked_ids != selected_ids:
        raise _auth_error(
            "lock auth provider order/metadata does not match the manifest; "
            "run atlas-compose resolve again",
        )
    if lock.auth.default != manifest.auth.default:
        raise _auth_error(
            "lock auth.default does not match the manifest; run "
            "atlas-compose resolve again",
        )
    locked_by_id = {provider.id: provider for provider in lock.auth.providers}
    for provider_id in selected_ids:
        owner, contribution = contributions[provider_id]
        descriptor = contribution.descriptor
        locked = locked_by_id[provider_id]
        if (
            locked.owner != owner
            or locked.flow_kind != descriptor.flow_kind.value
            or locked.contract_version != descriptor.contract_version
        ):
            raise _auth_error(
                f"locked metadata for {provider_id!r} is incompatible with "
                "its current owner, flow kind, or Plugin API contract; run "
                "atlas-compose resolve again",
            )


def check_search_engine_selection(manifest: Manifest) -> None:
    """An explicit `engine` for the search plugin must name a selected,
    non-disabled plugin with a backend. Only an explicit choice is checked
    here: no descriptor marks a plugin as an engine, so a missing or
    ambiguous engine is the search plugin's own startup error."""
    search = next((e for e in manifest.plugins if e.id == SEARCH_PLUGIN_ID), None)
    if search is None or search.disabled:
        return
    engine_id = search.config.get("engine")
    if engine_id is None:
        return
    engine = next((e for e in manifest.plugins if e.id == engine_id), None)
    if engine is None:
        raise InvalidSearchEngineSelectionError(
            engine_id, "that plugin is not in the manifest"
        )
    if engine.disabled:
        raise InvalidSearchEngineSelectionError(engine_id, "that plugin is disabled")
    if engine.backend is None:
        raise InvalidSearchEngineSelectionError(
            engine_id, "that plugin has no backend artifact"
        )


def check_no_duplicate_plugin_ids(manifest: Manifest) -> None:
    """A manifest naming the same plugin id twice can't be a resolution
    bug (each `PluginEntry` resolves independently) — it's an operator
    mistake worth failing on explicitly rather than silently letting the
    second entry win in the lock's `{id}@{version}`-keyed dict."""
    seen: set[str] = set()
    for entry in manifest.plugins:
        if entry.id in seen:
            raise DuplicatePluginIdError(entry.id)
        seen.add(entry.id)


def check_backend_frontend_versions_match(lock: Lock) -> None:
    """Defense-in-depth: `resolver.resolve_manifest` already guarantees
    this for a lock it produced itself (both artifacts are checked
    against the same manifest-declared version), but a lock is a
    checked-in file another tool or a hand-edit could produce differently
    — composition validation must catch that on the lock's own terms."""
    for key, locked in lock.plugins.items():
        if (
            locked.backend is not None
            and locked.frontend is not None
            and locked.backend.version != locked.frontend.version
        ):
            raise ArtifactVersionMismatchError(
                key,
                locked.backend.version,
                locked.frontend.version,
            )


def check_core_compatibility(
    manifest: Manifest,
    descriptors: Mapping[str, PluginDescriptor],
) -> None:
    for entry in manifest.plugins:
        descriptor = descriptors.get(entry.id)
        if descriptor is None:
            continue
        required_range = descriptor.compatibility.get("atlasCore")
        if required_range is None:
            continue
        if not range_contains(required_range, manifest.core.version):
            raise IncompatibleCoreRangeError(
                entry.id,
                manifest.core.version,
                required_range,
            )


def check_dependencies(
    manifest: Manifest,
    descriptors: Mapping[str, PluginDescriptor],
) -> None:
    """Mirrors `server.apps.plugins.composition._check_plugin_dependencies`,
    at the manifest level instead of over already-imported descriptors —
    so a missing dependency fails before `django.setup()` is even
    attempted."""
    selected_ids = {entry.id for entry in manifest.plugins}
    for entry in manifest.plugins:
        descriptor = descriptors.get(entry.id)
        if descriptor is None:
            continue
        missing = set(descriptor.requires_plugins) - selected_ids
        if missing:
            raise MissingDependencyError(entry.id, frozenset(missing))


def check_no_dependency_cycle(
    manifest: Manifest,
    descriptors: Mapping[str, PluginDescriptor],
) -> None:
    graph = {
        entry.id: set(descriptors[entry.id].requires_plugins)
        for entry in manifest.plugins
        if entry.id in descriptors
    }
    visiting: set[str] = set()
    visited: set[str] = set()
    path: list[str] = []

    def visit(node: str) -> None:
        if node in visited:
            return
        if node in visiting:
            cycle_start = path.index(node)
            raise DependencyCycleError((*path[cycle_start:], node))
        visiting.add(node)
        path.append(node)
        for dependency in graph.get(node, ()):
            if dependency in graph:
                visit(dependency)
        path.pop()
        visiting.discard(node)
        visited.add(node)

    for node in graph:
        visit(node)


RESERVED_SERVICE_IDS = frozenset(
    {"postgres", "initializer", "backend", "ingestor", "frontend"}
)
"""Compose service names the base `docker-compose.yml` already uses."""

_SERVICE_DEFINITION_FIELDS = (
    "image",
    "port",
    "health_check",
    "data_path",
    "secret_env",
    "external",
    "address",
)


def check_required_services(
    manifest: Manifest,
    lock: Lock,
    descriptors: Mapping[str, PluginDescriptor],
) -> None:
    """Required services must be declarable, wirable and recorded in the lock.

    Skips plugins missing from `descriptors`, like the other descriptor-based
    checks.
    """
    selected = {entry.id: entry for entry in manifest.plugins if not entry.disabled}
    for plugin_id, entry in selected.items():
        descriptor = descriptors.get(plugin_id)
        if descriptor is None:
            continue
        declared = {service.id: service for service in descriptor.required_services}
        for service_id, override in entry.services.items():
            if service_id not in declared:
                raise InvalidRequiredServiceError(
                    f"{plugin_id!r} configures service {service_id!r}, which it "
                    "does not declare",
                )
            if override.external and override.address is None:
                raise InvalidRequiredServiceError(
                    f"{plugin_id!r} marks service {service_id!r} as external "
                    "but gives no address",
                )
        for service in declared.values():
            if service.id in RESERVED_SERVICE_IDS:
                raise InvalidRequiredServiceError(
                    f"{plugin_id!r} declares service {service.id!r}, which is "
                    "reserved by the base deployment",
                )
            schema = descriptor.config_schema
            fields = set(schema.model_fields) if schema is not None else set()
            for key, field_name in service.config_keys.items():
                if field_name not in fields:
                    raise InvalidRequiredServiceError(
                        f"{plugin_id!r} cannot wire service {service.id!r}: "
                        f"{key} key {field_name!r} is not a field of its "
                        "configuration schema",
                    )

    resolved = resolve_required_services(manifest, descriptors)
    seen: dict[str, str] = {}
    for key, service in resolved.items():
        first = seen.setdefault(service.id, key)
        if first == key:
            continue
        other = resolved[first]
        for field_name in _SERVICE_DEFINITION_FIELDS:
            if getattr(service, field_name) != getattr(other, field_name):
                raise ConflictingServiceError(
                    service.id, other.plugin, service.plugin, field_name
                )

    if lock.services != resolved:
        raise InvalidRequiredServiceError(
            "lock required services do not match the manifest and plugin "
            "declarations; run atlas-compose resolve again",
        )


def check_plugin_config(
    manifest: Manifest,
    descriptors: Mapping[str, PluginDescriptor],
) -> None:
    """Validates each manifest plugin entry's `config` block against its
    descriptor's `config_schema`, if it declares one — structural
    (non-secret) validation only, matching
    `plugin-architecture.md:549-558`'s "invalid non-secret configuration".
    A `fromEnv` secret reference validates as a valid `SecretRef` shape,
    never resolved (no environment access happens here)."""
    services = resolve_required_services(manifest, descriptors)
    for entry in manifest.plugins:
        descriptor = descriptors.get(entry.id)
        if descriptor is None or descriptor.config_schema is None:
            continue
        try:
            descriptor.config_schema.model_validate(
                wire_plugin_config(entry.id, entry.config, services)
            )
        except ValidationError as exc:
            raise InvalidPluginConfigError(entry.id, str(exc)) from exc


def validate_composition(
    manifest: Manifest,
    lock: Lock,
    descriptors: Mapping[str, PluginDescriptor] | None = None,
) -> None:
    """Run every static composition-validation rule in fail-fast order.

    `descriptors` (plugin id -> its real `PluginDescriptor`, e.g. from
    `descriptors.load_backend_descriptors`) is optional: checks that need
    it are skipped for any plugin id missing from the mapping, so a
    frontend-only or not-yet-importable plugin doesn't block the checks
    that don't need it.
    """
    descriptors = descriptors or {}
    check_no_duplicate_plugin_ids(manifest)
    check_authentication_selection(manifest, lock, descriptors)
    check_search_engine_selection(manifest)
    check_required_services(manifest, lock, descriptors)
    check_backend_frontend_versions_match(lock)
    check_core_compatibility(manifest, descriptors)
    check_dependencies(manifest, descriptors)
    check_no_dependency_cycle(manifest, descriptors)
    check_plugin_config(manifest, descriptors)
