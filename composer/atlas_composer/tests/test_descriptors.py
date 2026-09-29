"""Real backend descriptor loading tests (`composition-validation` spec) —
uses this monorepo's own real plugin packages, importable in this shared
virtualenv (`core/backend/pyproject.toml`'s path dependencies), unlike
`test_composition.py`'s synthetic fixtures."""

from atlas_composer.descriptors import load_backend_descriptors
from atlas_composer.lock import Lock, LockedBackendArtifact, LockedPlugin


def test_load_backend_descriptors_imports_the_real_plugin_module():
    lock = Lock(
        distribution="company.atlas@2026.08",
        core="0.1.0",
        plugins={
            "atlas.c4@0.1.0": LockedPlugin(
                backend=LockedBackendArtifact(
                    package="atlas-plugin-c4",
                    version="0.1.0",
                    hash="sha256:x",
                ),
            ),
        },
    )

    descriptors = load_backend_descriptors(lock)

    assert descriptors.keys() == {"atlas.c4"}
    descriptor = descriptors["atlas.c4"]
    assert descriptor.id == "atlas.c4"
    assert descriptor.compatibility == {"atlasCore": ">=0.1 <1"}
    assert descriptor.requires_plugins == {
        "atlas.standard-catalog": ">=0.1 <1",
    }


def test_load_backend_descriptors_skips_frontend_only_plugins():
    lock = Lock(
        distribution="company.atlas@2026.08",
        core="0.1.0",
        plugins={
            "atlas.apis@0.1.0": LockedPlugin(backend=None),
        },
    )

    descriptors = load_backend_descriptors(lock)

    assert descriptors == {}
