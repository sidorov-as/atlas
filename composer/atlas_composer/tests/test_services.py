"""Required-service tests (`deployment-required-services` spec): lock,
validation, wiring and the generated compose override."""

import pytest
import yaml
from atlas_plugin_api import PluginConfigSchema, PluginDescriptor, RequiredService
from pydantic import ValidationError

from atlas_composer.composition import (
    ConflictingServiceError,
    InvalidPluginConfigError,
    InvalidRequiredServiceError,
    check_plugin_config,
    check_required_services,
)
from atlas_composer.generate import (
    generate_compose_services,
    generate_plugin_configs,
    render_compose_services,
)
from atlas_composer.lock import Lock, LockedBackendArtifact, LockedPlugin, dump_lock
from atlas_composer.manifest import Manifest
from atlas_composer.resolver import resolve_manifest
from atlas_composer.services import secret_from_env_name

from .test_resolver import REPO_ROOT


class _EngineConfig(PluginConfigSchema):
    url: str
    api_key: str | dict | None = None


def _service(**overrides) -> RequiredService:
    fields = {
        "id": "meilisearch",
        "purpose": "Search index",
        "image": "getmeili/meilisearch:v1.12",
        "port": 7700,
        "health_check": ("curl", "-f", "http://localhost:7700/health"),
        "config_keys": {"address": "url", "secret": "api_key"},
        "secret_env": "MEILI_MASTER_KEY",
        "data_path": "/meili_data",
    }
    fields.update(overrides)
    return RequiredService(**fields)


def _descriptor(plugin_id: str, *services: RequiredService) -> PluginDescriptor:
    return PluginDescriptor(
        id=plugin_id,
        version="0.1.0",
        compatibility={},
        django_apps=(),
        entry_point="example.plugin:PLUGIN",
        config_schema=_EngineConfig,
        required_services=services,
    )


def _entry(plugin_id: str, **extra) -> dict:
    return {
        "id": plugin_id,
        "version": "0.1.0",
        "backend": {
            "package": "atlas-plugin-standard-catalog",
            "source": "workspace",
        },
        **extra,
    }


def _manifest(*plugins: dict) -> Manifest:
    return Manifest.model_validate(
        {
            "distribution": {"id": "company.atlas", "version": "2026.08"},
            "core": {"version": "0.1.0"},
            "plugins": list(plugins),
        }
    )


def _resolve(manifest: Manifest, *descriptors: PluginDescriptor) -> Lock:
    # The real package behind every entry only supplies native lock hashes;
    # the declared services come from the synthetic descriptors.
    resolved = {d.id: d for d in descriptors}
    return resolve_manifest(manifest, repo_root=REPO_ROOT, descriptors=resolved)


ENGINE = "atlas.search-meili"
OTHER = "atlas.other-meili"


def test_no_services_leaves_the_lock_and_compose_inputs_empty(tmp_path):
    manifest = _manifest(_entry(ENGINE, config={"url": "http://x"}))
    lock = _resolve(manifest, _descriptor(ENGINE))

    assert lock.services == {}
    assert generate_compose_services(lock) == {}
    assert generate_plugin_configs(lock) == {ENGINE: {"url": "http://x"}}
    path = tmp_path / "lock.yaml"
    dump_lock(lock, path)
    assert "services" not in yaml.safe_load(path.read_text())
    check_required_services(manifest, lock, {ENGINE: _descriptor(ENGINE)})


def test_one_service_is_locked_wired_and_composed():
    descriptor = _descriptor(ENGINE, _service())
    lock = _resolve(_manifest(_entry(ENGINE)), descriptor)

    locked = lock.services[f"{ENGINE}/meilisearch"]
    assert locked.image == "getmeili/meilisearch:v1.12"
    assert locked.secret_from_env == "ATLAS_SERVICE_MEILISEARCH_KEY"

    assert generate_plugin_configs(lock)[ENGINE] == {
        "url": "http://meilisearch:7700",
        "api_key": {"fromEnv": "ATLAS_SERVICE_MEILISEARCH_KEY"},
    }

    compose = generate_compose_services(lock)
    service = compose["services"]["meilisearch"]
    assert service["image"] == "getmeili/meilisearch:v1.12"
    assert service["volumes"] == ["meilisearch-data:/meili_data"]
    assert compose["volumes"] == {"meilisearch-data": {}}
    assert service["environment"] == {
        "MEILI_MASTER_KEY": "${ATLAS_SERVICE_MEILISEARCH_KEY}"
    }
    for name in ("initializer", "backend", "ingestor"):
        assert compose["services"][name]["depends_on"] == {
            "meilisearch": {"condition": "service_healthy"}
        }
        assert (
            "ATLAS_SERVICE_MEILISEARCH_KEY" in compose["services"][name]["environment"]
        )
    check_required_services(_manifest(_entry(ENGINE)), lock, {ENGINE: descriptor})


def test_the_lock_never_holds_a_secret_value(monkeypatch, tmp_path):
    monkeypatch.setenv("ATLAS_SERVICE_MEILISEARCH_KEY", "s3cret-value")
    lock = _resolve(_manifest(_entry(ENGINE)), _descriptor(ENGINE, _service()))
    path = tmp_path / "lock.yaml"
    dump_lock(lock, path)

    assert "s3cret-value" not in path.read_text()
    assert "ATLAS_SERVICE_MEILISEARCH_KEY" in path.read_text()


def test_a_service_without_data_generates_no_volume():
    lock = _resolve(
        _manifest(_entry(ENGINE)),
        _descriptor(ENGINE, _service(data_path=None)),
    )

    compose = generate_compose_services(lock)
    assert "volumes" not in compose
    assert "volumes" not in compose["services"]["meilisearch"]


def test_an_external_service_generates_no_container_but_wires_the_address():
    manifest = _manifest(
        _entry(
            ENGINE,
            services={
                "meilisearch": {"external": True, "address": "http://search.lan:7700/"}
            },
        )
    )
    descriptor = _descriptor(ENGINE, _service())
    lock = _resolve(manifest, descriptor)

    assert generate_plugin_configs(lock)[ENGINE]["url"] == "http://search.lan:7700"
    compose = generate_compose_services(lock)
    assert "meilisearch" not in compose["services"]
    assert "volumes" not in compose
    assert "depends_on" not in compose["services"]["backend"]
    assert (
        "ATLAS_SERVICE_MEILISEARCH_KEY" in compose["services"]["backend"]["environment"]
    )
    check_required_services(manifest, lock, {ENGINE: descriptor})


def test_an_external_service_without_an_address_fails_naming_it():
    manifest = _manifest(_entry(ENGINE, services={"meilisearch": {"external": True}}))
    descriptor = _descriptor(ENGINE, _service())
    lock = _resolve(manifest, descriptor)

    with pytest.raises(InvalidRequiredServiceError, match="meilisearch.*no address"):
        check_required_services(manifest, lock, {ENGINE: descriptor})


def test_an_address_requires_external():
    with pytest.raises(ValidationError, match="external"):
        _manifest(_entry(ENGINE, services={"meilisearch": {"address": "http://x"}}))


def test_an_explicit_operator_value_wins_over_wiring():
    manifest = _manifest(_entry(ENGINE, config={"url": "http://override:1"}))
    lock = _resolve(manifest, _descriptor(ENGINE, _service()))

    assert generate_plugin_configs(lock)[ENGINE]["url"] == "http://override:1"


def test_a_service_the_plugin_does_not_declare_fails():
    manifest = _manifest(_entry(ENGINE, services={"redis": {"external": True}}))
    descriptor = _descriptor(ENGINE, _service())
    lock = _resolve(manifest, descriptor)

    with pytest.raises(InvalidRequiredServiceError, match="'redis'"):
        check_required_services(manifest, lock, {ENGINE: descriptor})


def test_a_service_that_cannot_be_wired_to_the_config_fails():
    descriptor = _descriptor(
        ENGINE, _service(config_keys={"address": "endpoint", "secret": "api_key"})
    )
    manifest = _manifest(_entry(ENGINE))
    lock = _resolve(manifest, descriptor)

    with pytest.raises(InvalidRequiredServiceError, match="endpoint"):
        check_required_services(manifest, lock, {ENGINE: descriptor})


def test_a_reserved_service_id_fails():
    descriptor = _descriptor(ENGINE, _service(id="backend"))
    manifest = _manifest(_entry(ENGINE))
    lock = _resolve(manifest, descriptor)

    with pytest.raises(InvalidRequiredServiceError, match="reserved"):
        check_required_services(manifest, lock, {ENGINE: descriptor})


def test_conflicting_declarations_fail_naming_both_plugins():
    first = _descriptor(ENGINE, _service())
    second = _descriptor(OTHER, _service(image="getmeili/meilisearch:v1.13"))
    manifest = _manifest(_entry(ENGINE), _entry(OTHER))
    lock = _resolve(manifest, first, second)

    with pytest.raises(ConflictingServiceError) as raised:
        check_required_services(manifest, lock, {ENGINE: first, OTHER: second})
    assert ENGINE in str(raised.value)
    assert OTHER in str(raised.value)
    assert "image" in str(raised.value)


def test_identical_declarations_share_one_container():
    first = _descriptor(ENGINE, _service())
    second = _descriptor(OTHER, _service())
    manifest = _manifest(_entry(ENGINE), _entry(OTHER))
    lock = _resolve(manifest, first, second)

    check_required_services(manifest, lock, {ENGINE: first, OTHER: second})
    assert list(generate_compose_services(lock)["services"]).count("meilisearch") == 1
    assert len(lock.services) == 2


def test_a_plugin_that_is_not_selected_adds_no_service():
    other = _descriptor(OTHER)
    manifest = _manifest(_entry(OTHER))
    lock = _resolve(manifest, other, _descriptor(ENGINE, _service()))

    assert lock.services == {}


def test_a_disabled_plugin_adds_no_service():
    manifest = _manifest(_entry(ENGINE, disabled=True))
    lock = _resolve(manifest, _descriptor(ENGINE, _service()))

    assert lock.services == {}


def test_the_lock_is_reproducible():
    manifest = _manifest(_entry(ENGINE))
    descriptor = _descriptor(ENGINE, _service())

    first = _resolve(manifest, descriptor)
    second = _resolve(manifest, descriptor)

    assert first.services == second.services
    assert render_compose_services(first) == render_compose_services(second)


def test_a_stale_lock_fails_validation():
    manifest = _manifest(_entry(ENGINE))
    descriptor = _descriptor(ENGINE, _service())
    stale = Lock(
        distribution="company.atlas@2026.08",
        core="0.1.0",
        plugins={
            f"{ENGINE}@0.1.0": LockedPlugin(
                backend=LockedBackendArtifact(
                    package="atlas-plugin-standard-catalog", version="0.1.0", hash="h"
                )
            )
        },
    )

    with pytest.raises(InvalidRequiredServiceError, match="resolve again"):
        check_required_services(manifest, stale, {ENGINE: descriptor})


def test_plugin_config_is_validated_after_wiring():
    # `url` is required by the schema; only the wired address supplies it.
    descriptor = _descriptor(ENGINE, _service())
    check_plugin_config(_manifest(_entry(ENGINE)), {ENGINE: descriptor})

    with pytest.raises(InvalidPluginConfigError):
        check_plugin_config(_manifest(_entry(ENGINE)), {ENGINE: _descriptor(ENGINE)})


def test_rendered_compose_is_valid_yaml_with_the_generated_header():
    lock = _resolve(_manifest(_entry(ENGINE)), _descriptor(ENGINE, _service()))
    text = render_compose_services(lock)

    assert text.startswith("# GENERATED")
    assert yaml.safe_load(text)["services"]["meilisearch"]["image"].startswith(
        "getmeili"
    )


def test_secret_env_name_is_derived_from_the_service_id():
    assert secret_from_env_name("my-search") == "ATLAS_SERVICE_MY_SEARCH_KEY"
