"""Plugin descriptor tests (plugin-registries spec)."""

import dataclasses
import os
import subprocess
import sys

import pytest

from atlas_plugin_api import (
    PLUGIN_ENTRY_POINT_GROUP,
    AuthenticationFlowKind,
    AuthenticationProviderContribution,
    AuthenticationProviderDescriptor,
    AuthenticationProviderPresentation,
    PluginConfigSchema,
    PluginDescriptor,
)


def _descriptor(**overrides):
    fields = {
        "id": "atlas.catalog",
        "version": "0.1.0",
        "compatibility": {"atlasCore": ">=0.1 <1"},
        "django_apps": ("server.apps.catalog",),
        "entry_point": "server.apps.catalog.plugin:PLUGIN",
    }
    fields.update(overrides)
    return PluginDescriptor(**fields)


def test_descriptor_exposes_the_declared_static_metadata():
    descriptor = _descriptor()

    assert descriptor.id == "atlas.catalog"
    assert descriptor.version == "0.1.0"
    assert descriptor.compatibility == {"atlasCore": ">=0.1 <1"}
    assert descriptor.django_apps == ("server.apps.catalog",)
    assert descriptor.entry_point == "server.apps.catalog.plugin:PLUGIN"


def test_descriptor_is_immutable():
    descriptor = _descriptor()

    with pytest.raises(dataclasses.FrozenInstanceError):
        descriptor.version = "0.2.0"


def test_descriptor_is_importable_without_django_models():
    # A regression guard for the "readable before django.setup()" requirement:
    # importing the module must not reach into `django.db.models` or the app
    # registry. If it did, this import would already have failed under
    # pytest-django's plain module import (no fixtures used here).
    import atlas_plugin_api.descriptor as descriptor_module

    assert hasattr(descriptor_module, "PluginDescriptor")


def test_entry_point_group_matches_the_declared_convention():
    assert PLUGIN_ENTRY_POINT_GROUP == "atlas.plugins"


def test_descriptor_carries_static_authentication_provider_contributions():
    provider = AuthenticationProviderDescriptor(
        id="atlas.auth.fixture",
        flow_kind=AuthenticationFlowKind.REDIRECT,
        presentation=AuthenticationProviderPresentation(display_name="Fixture SSO"),
    )
    contribution = AuthenticationProviderContribution(
        descriptor=provider,
        django_apps=("atlas_auth_fixture",),
        url_modules=("atlas_auth_fixture.urls",),
    )

    descriptor = _descriptor(authentication_providers=(contribution,))

    assert descriptor.authentication_providers == (contribution,)
    assert descriptor.authentication_providers[0].descriptor.id == "atlas.auth.fixture"


def test_descriptor_rejects_duplicate_authentication_provider_contributions():
    provider = AuthenticationProviderDescriptor(
        id="atlas.auth.fixture",
        flow_kind=AuthenticationFlowKind.REDIRECT,
        presentation=AuthenticationProviderPresentation(display_name="Fixture SSO"),
    )
    contribution = AuthenticationProviderContribution(descriptor=provider)

    with pytest.raises(ValueError, match="duplicate authentication provider ids"):
        _descriptor(authentication_providers=(contribution, contribution))


def test_authentication_contribution_validates_source_and_group_capabilities():
    class Config(PluginConfigSchema):
        authority: str

    provider = AuthenticationProviderDescriptor(
        id="atlas.auth.fixture",
        flow_kind=AuthenticationFlowKind.REDIRECT,
        presentation=AuthenticationProviderPresentation(display_name="Fixture SSO"),
    )
    contribution = AuthenticationProviderContribution(
        descriptor=provider,
        config_schema=Config,
        source_id_config_field="authority",
        supported_group_sync_modes=("none",),
    )

    assert contribution.source_id_config_field == "authority"
    assert contribution.supported_group_sync_modes == ("none",)

    with pytest.raises(ValueError, match="source_id_config_field"):
        AuthenticationProviderContribution(
            descriptor=provider,
            config_schema=Config,
            source_id_config_field="missing",
        )
    with pytest.raises(ValueError, match="supported_group_sync_modes"):
        AuthenticationProviderContribution(
            descriptor=provider,
            supported_group_sync_modes=("none", "none"),
        )


def test_descriptor_with_authentication_contribution_imports_before_django_setup():
    environment = dict(os.environ)
    environment.pop("DJANGO_SETTINGS_MODULE", None)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "sys.addaudithook(lambda event, args: (_ for _ in ()).throw("
                "RuntimeError(event)) if event.startswith('socket.') or "
                "event.endswith('.connect') else None); "
                "from django.apps import apps; assert not apps.ready; "
                "from atlas_plugin_api import ("
                "AuthenticationFlowKind, AuthenticationProviderContribution, "
                "AuthenticationProviderDescriptor, AuthenticationProviderPresentation, "
                "PluginDescriptor); "
                "provider = AuthenticationProviderDescriptor(id='atlas.auth.fixture', "
                "flow_kind=AuthenticationFlowKind.REDIRECT, "
                "presentation=AuthenticationProviderPresentation(display_name='SSO')); "
                "PluginDescriptor(id='fixture', version='0.1.0', compatibility={}, "
                "django_apps=(), entry_point='fixture:PLUGIN', "
                "authentication_providers=(AuthenticationProviderContribution("
                "descriptor=provider),)); assert not apps.ready"
            ),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode == 0, result.stderr
