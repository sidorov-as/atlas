"""Required external services: declaration -> lock entry -> wired config.

A plugin declares what it needs in `PluginDescriptor.required_services`; the
manifest's `plugins[].services` block lets the operator point one at an
instance they already run. Everything here is pure: no environment access, so
a secret only ever appears as the *name* of the environment variable that
carries it.
"""

from collections.abc import Mapping
from typing import Any

from atlas_plugin_api import PluginDescriptor, RequiredService

from .lock import LockedService
from .manifest import Manifest


def service_key(plugin_id: str, service_id: str) -> str:
    return f"{plugin_id}/{service_id}"


def secret_from_env_name(service_id: str) -> str:
    """Environment variable the operator sets for the service's access key."""
    return f"ATLAS_SERVICE_{service_id.upper().replace('-', '_')}_KEY"


def generated_address(service: LockedService) -> str:
    return f"http://{service.id}:{service.port}"


def _lock_service(
    plugin_id: str,
    service: RequiredService,
    *,
    external: bool,
    address: str | None,
) -> LockedService:
    secret_field = service.config_keys.get("secret")
    return LockedService(
        plugin=plugin_id,
        id=service.id,
        image=service.image,
        port=service.port,
        healthCheck=service.health_check,
        addressKey=service.config_keys["address"],
        secretKey=secret_field,
        secretEnv=service.secret_env,
        secretFromEnv=(
            secret_from_env_name(service.id) if secret_field is not None else None
        ),
        dataPath=service.data_path,
        external=external,
        address=address,
    )


def resolve_required_services(
    manifest: Manifest,
    descriptors: Mapping[str, PluginDescriptor],
) -> dict[str, LockedService]:
    """Lock entries for every enabled plugin that declares a service, in
    manifest order. Operator choices for a service the plugin does not declare
    are left for `composition.check_required_services` to report."""
    resolved: dict[str, LockedService] = {}
    for entry in manifest.plugins:
        descriptor = descriptors.get(entry.id)
        if descriptor is None or entry.disabled:
            continue
        for service in descriptor.required_services:
            override = entry.services.get(service.id)
            resolved[service_key(entry.id, service.id)] = _lock_service(
                entry.id,
                service,
                external=override is not None and override.external,
                address=override.address if override is not None else None,
            )
    return resolved


def wire_plugin_config(
    plugin_id: str,
    config: Mapping[str, Any],
    services: Mapping[str, LockedService],
) -> dict[str, Any]:
    """`config` plus the address and secret reference each of the plugin's
    services supplies. A value the operator wrote explicitly always wins."""
    wired = dict(config)
    for service in services.values():
        if service.plugin != plugin_id:
            continue
        address = service.address if service.external else generated_address(service)
        if address is not None:
            wired.setdefault(service.address_key, address)
        if service.secret_key is not None and service.secret_from_env is not None:
            wired.setdefault(service.secret_key, {"fromEnv": service.secret_from_env})
    return wired
