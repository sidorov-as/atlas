import os
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

import pytest
from atlas_plugin_api import RemoteLogoutCapability, SecretRef
from pydantic import ValidationError

from atlas_plugin_auth_gitea.config import GiteaConfig
from atlas_plugin_auth_gitea.plugin import (
    PLUGIN,
    PROVIDER_ID,
    SUPPORTED_ALLAUTH_VERSION,
    SUPPORTED_GITEA_VERSION,
)


def _config(**overrides):
    values = {
        "instanceOrigin": "https://gitea.example",
        "clientId": "atlas",
        "clientSecret": {"fromEnv": "ATLAS_GITEA_CLIENT_SECRET"},
    }
    values.update(overrides)
    return GiteaConfig.model_validate(values)


def test_static_descriptor_declares_typed_redirect_provider():
    contribution = PLUGIN.authentication_providers[0]

    assert PLUGIN.id == PROVIDER_ID
    assert contribution.descriptor.id == PROVIDER_ID
    assert contribution.descriptor.flow_kind.value == "redirect"
    assert (
        contribution.descriptor.remote_logout
        is RemoteLogoutCapability.UNSUPPORTED
    )
    assert contribution.config_schema is GiteaConfig
    assert contribution.django_apps == ("atlas_plugin_auth_gitea",)
    assert contribution.source_id_config_field == "instance_origin"
    assert contribution.supported_group_sync_modes == ("none",)


def test_static_descriptor_import_does_not_require_django_setup():
    environment = dict(os.environ)
    environment.pop("DJANGO_SETTINGS_MODULE", None)
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(
            None,
            (
                str(Path(__file__).resolve().parents[2]),
                environment.get("PYTHONPATH"),
            ),
        )
    )

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from atlas_plugin_auth_gitea.plugin import PLUGIN;"
            " print(PLUGIN.id)",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == PROVIDER_ID


def test_config_keeps_client_secret_as_an_unresolved_reference():
    config = _config()

    assert config.instance_origin == "https://gitea.example"
    assert config.scopes == ("read:user",)
    assert isinstance(config.client_secret, SecretRef)
    assert config.has_unresolved_secrets()


@pytest.mark.parametrize(
    "overrides",
    [
        {"scopes": []},
        {"scopes": ["read:user", "read:organization"]},
        {"scopes": ["openid"]},
        {"oauthPkceEnabled": False},
        {"instanceOrigin": "https://gitea.example/path"},
        {"instanceOrigin": "http://gitea.example"},
    ],
)
def test_config_rejects_unsupported_or_downgraded_combinations(overrides):
    with pytest.raises(ValidationError):
        _config(**overrides)


def test_loopback_http_requires_an_explicit_development_opt_in():
    config = _config(
        instanceOrigin="http://127.0.0.1:3000",
        allowDevelopmentHttp=True,
    )

    assert config.instance_origin == "http://127.0.0.1:3000"


def test_localhost_subdomain_supports_a_docker_development_alias():
    config = _config(
        instanceOrigin="http://gitea.localhost:18082",
        allowedDestinations=["http://gitea.localhost:18082"],
        allowDevelopmentHttp=True,
    )

    assert config.instance_origin == "http://gitea.localhost:18082"


def test_supported_adapter_baseline_is_pinned_and_documented():
    assert SUPPORTED_ALLAUTH_VERSION == "65.19.1"
    assert SUPPORTED_GITEA_VERSION == "1.27.3"


def test_pinned_allauth_gitea_adapter_matches_the_supported_endpoints(settings):
    from allauth.socialaccount.providers.gitea.views import GiteaOAuth2Adapter

    assert version("django-allauth") == SUPPORTED_ALLAUTH_VERSION
    assert GiteaOAuth2Adapter.authorize_url.endswith("/login/oauth/authorize")
    assert GiteaOAuth2Adapter.access_token_url.endswith(
        "/login/oauth/access_token"
    )
    assert GiteaOAuth2Adapter.profile_url.endswith("/api/v1/user")
