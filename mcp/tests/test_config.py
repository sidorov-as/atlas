import pytest
from atlas_mcp.config import ConfigError, load_config


def test_load_config_returns_config_from_env():
    config = load_config(
        {"ATLAS_API_URL": "http://localhost:8000/", "ATLAS_PAT": "atlaspat_x"}
    )

    # Trailing slash stripped so `openapi_url` never doubles one up.
    assert config.api_url == "http://localhost:8000"
    assert config.pat == "atlaspat_x"


def test_openapi_url_targets_the_mcp_plugins_own_schema_endpoint():
    config = load_config(
        {"ATLAS_API_URL": "http://localhost:8000", "ATLAS_PAT": "atlaspat_x"}
    )

    assert (
        config.openapi_url == "http://localhost:8000/api/plugins/atlas.mcp/openapi.json"
    )


def test_load_config_raises_when_atlas_api_url_is_missing():
    with pytest.raises(ConfigError, match="ATLAS_API_URL"):
        load_config({"ATLAS_PAT": "atlaspat_x"})


def test_load_config_raises_when_atlas_pat_is_missing():
    with pytest.raises(ConfigError, match="ATLAS_PAT"):
        load_config({"ATLAS_API_URL": "http://localhost:8000"})


def test_load_config_names_every_missing_variable_at_once():
    with pytest.raises(ConfigError, match="ATLAS_API_URL, ATLAS_PAT"):
        load_config({})
