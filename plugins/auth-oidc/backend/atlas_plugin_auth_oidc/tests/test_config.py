import os
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from atlas_plugin_auth_oidc.config import OIDCConfig
from atlas_plugin_auth_oidc.plugin import PLUGIN, PROVIDER_ID


def _config(**overrides):
    values = {
        "discoveryUrl": "https://idp.example/.well-known/openid-configuration",
        "expectedIssuer": "https://idp.example",
        "clientId": "atlas",
        "clientSecret": "test-secret",
    }
    values.update(overrides)
    return OIDCConfig.model_validate(values)


def test_static_descriptor_declares_typed_redirect_provider():
    contribution = PLUGIN.authentication_providers[0]

    assert PLUGIN.id == PROVIDER_ID
    assert contribution.descriptor.id == PROVIDER_ID
    assert contribution.descriptor.flow_kind.value == "redirect"
    assert contribution.config_schema is OIDCConfig


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
            "from atlas_plugin_auth_oidc.plugin import PLUGIN;"
            " print(PLUGIN.id)",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == PROVIDER_ID


def test_config_separates_discovery_url_and_expected_issuer():
    config = _config()

    assert config.discovery_url.endswith("openid-configuration")
    assert config.expected_issuer == "https://idp.example"


@pytest.mark.parametrize(
    "overrides",
    [
        {"scopes": ["profile"]},
        {"allowedAlgorithms": ["HS256"]},
        {"allowedAlgorithms": ["none"]},
    ],
)
def test_config_rejects_unsafe_protocol_baselines(overrides):
    with pytest.raises(ValidationError):
        _config(**overrides)


def test_config_allows_development_http_for_localhost_subdomains_only():
    config = _config(
        allowedDestinations=["http://keycloak.localhost:18081"],
        allowDevelopmentHttp=True,
    )

    assert config.allowed_destinations == ("http://keycloak.localhost:18081",)

    with pytest.raises(ValidationError):
        _config(
            allowedDestinations=["http://keycloak.example.test:18081"],
            allowDevelopmentHttp=True,
        )
