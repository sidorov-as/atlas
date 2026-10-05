"""The Meilisearch example distribution and the exactly-one-engine rule.

Spans the composer, the search plugin and both engine adapters, which may not
import each other, so it lives with core's tests (`search-meilisearch-engine`
spec: "Meilisearch is a selectable engine plugin").
"""

from pathlib import Path

import pytest
from atlas_composer.composition import validate_composition
from atlas_composer.descriptors import load_backend_descriptors
from atlas_composer.generate import (
    generate_compose_services,
    generate_plugin_configs,
)
from atlas_composer.lock import load_lock
from atlas_composer.manifest import load_manifest
from atlas_plugin_api import (
    SearchEngineSelectionError,
    register_search_engine,
)
from atlas_plugin_api import search as search_contract
from atlas_plugin_api.permissions import registry as permission_registry
from atlas_plugin_search import plugin, runtime
from atlas_plugin_search.config import SearchPluginConfig
from atlas_plugin_search_meilisearch.config import SearchMeilisearchPluginConfig
from atlas_plugin_search_meilisearch.engine import MeilisearchSearchEngine
from atlas_plugin_search_postgres.engine import PostgresSearchEngine

REPO_ROOT = Path(__file__).resolve().parents[4]
MEILI = "atlas.search-meilisearch"
POSTGRES = "atlas.search-postgres"


def _load(directory: str):
    root = REPO_ROOT / directory
    return load_manifest(root / "manifest.yaml"), load_lock(root / "lock.yaml")


def _selected(manifest) -> set[str]:
    return {entry.id for entry in manifest.plugins if not entry.disabled}


def test_example_selects_meilisearch_instead_of_the_default_engine():
    manifest, lock = _load("examples/search-meilisearch")

    assert MEILI in _selected(manifest)
    assert POSTGRES not in _selected(manifest)
    descriptors = load_backend_descriptors(lock)
    validate_composition(manifest, lock, descriptors)


def test_example_lock_records_the_service_and_wires_the_plugin():
    _, lock = _load("examples/search-meilisearch")

    (service,) = lock.services.values()
    assert service.plugin == MEILI
    assert service.image.startswith("getmeili/meilisearch:")
    config = generate_plugin_configs(lock)[MEILI]
    assert config["url"] == f"http://meilisearch:{service.port}"
    assert config["key"] == {"fromEnv": service.secret_from_env}
    assert "meilisearch" in generate_compose_services(lock)["services"]


def test_default_distribution_keeps_postgres_and_needs_no_service():
    manifest, lock = _load("distributions/default")

    assert POSTGRES in _selected(manifest)
    assert MEILI not in _selected(manifest)
    assert not lock.services
    assert generate_compose_services(lock) == {}
    assert MEILI not in generate_plugin_configs(lock)


def test_demo_distribution_keeps_postgres_and_needs_no_service():
    manifest, lock = _load("deploy/render")

    assert POSTGRES in _selected(manifest)
    assert MEILI not in _selected(manifest)
    assert not lock.services
    assert generate_compose_services(lock) == {}


@pytest.fixture
def clean_registries():
    def reset():
        search_contract._search_engine_registry.__init__()
        permission_registry._owners.pop(plugin.STATUS_ADMIN_PERMISSION, None)
        permission_registry._effects.pop(plugin.STATUS_ADMIN_PERMISSION, None)
        runtime.reset()

    reset()
    yield
    reset()


@pytest.fixture
def both_engines(clean_registries):
    postgres = PostgresSearchEngine()
    meilisearch = MeilisearchSearchEngine(
        SearchMeilisearchPluginConfig(url="http://meilisearch:7700")
    )
    register_search_engine(postgres, owner=POSTGRES)
    register_search_engine(meilisearch, owner=MEILI)
    plugin.register_runtime()
    return postgres, meilisearch


def test_selecting_both_engines_fails_and_names_them(both_engines):
    with pytest.raises(SearchEngineSelectionError) as error:
        plugin.finalize_runtime()

    assert "postgres" in str(error.value)
    assert "meilisearch" in str(error.value)
    assert not runtime.is_active()


@pytest.mark.parametrize("choice", [POSTGRES, MEILI])
def test_the_engine_setting_resolves_the_ambiguity(both_engines, choice):
    runtime.configure(SearchPluginConfig(engine=choice))

    plugin.finalize_runtime()

    postgres, meilisearch = both_engines
    assert runtime.get_engine() is (
        postgres if choice == POSTGRES else meilisearch
    )
