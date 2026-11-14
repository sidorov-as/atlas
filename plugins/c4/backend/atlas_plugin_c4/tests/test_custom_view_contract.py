"""Request contract and error bodies of the custom view endpoint."""

from http import HTTPStatus
from uuid import uuid4

import pytest
from pydantic import ValidationError

from atlas_plugin_c4.api.schemas import CustomViewSettings
from atlas_plugin_c4.config import C4PluginConfig
from atlas_plugin_c4.errors import node_limit_exceeded, unknown_entity


def test_max_nodes_defaults_to_50_and_is_configurable():
    assert C4PluginConfig().max_nodes == 50
    assert C4PluginConfig.model_validate({"maxNodes": 80}).max_nodes == 80


@pytest.mark.parametrize("value", [0, -1])
def test_max_nodes_must_be_positive(value):
    with pytest.raises(ValidationError):
        C4PluginConfig.model_validate({"maxNodes": value})


def test_unknown_entity_error_names_the_entity():
    pk = uuid4()
    error = unknown_entity(pk)
    assert error.status_code == HTTPStatus.NOT_FOUND
    detail = error.body()["detail"][0]
    assert detail["type"] == "unknown_entity"
    assert detail["entity"] == str(pk)


def test_node_limit_error_reports_limit_and_count():
    error = node_limit_exceeded(limit=50, count=72)
    assert error.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    detail = error.body()["detail"][0]
    assert (detail["type"], detail["limit"], detail["count"]) == (
        "node_limit_exceeded",
        50,
        72,
    )


def _settings(**overrides):
    return CustomViewSettings.model_validate(
        {
            "level": "components",
            "selection": "neighborhood",
            "entities": [uuid4()],
            **overrides,
        }
    )


def test_settings_neighborhood_defaults():
    settings = _settings()
    assert (settings.depth, settings.direction) == (1, "both")
    assert settings.relationships == "declared"
    assert settings.entity_types is None


def test_settings_accept_camel_case_keys():
    settings = _settings(entityTypes=["api"], relationships="declared_and_derived")
    assert settings.entity_types == ["api"]
    assert settings.relationships == "declared_and_derived"


def test_settings_empty_entity_types_means_none_enabled():
    assert _settings(entityTypes=[]).entity_types == []


@pytest.mark.parametrize("depth, expected", [(3, 3), ("all", "all")])
def test_settings_depth_accepts_positive_integer_or_all(depth, expected):
    assert _settings(depth=depth).depth == expected


@pytest.mark.parametrize("depth", [0, -2, "many", 1.5])
def test_settings_invalid_depth_is_rejected(depth):
    with pytest.raises(ValidationError):
        _settings(depth=depth)


@pytest.mark.parametrize(
    "overrides",
    [
        {"entities": []},
        {"level": "containers"},
        {"selection": "everything"},
        {"direction": "sideways"},
        {"relationships": "all"},
        {"entityTypes": ["person"]},
        {"entityTypes": ["api", "api"]},
    ],
)
def test_settings_invalid_values_are_rejected(overrides):
    with pytest.raises(ValidationError):
        _settings(**overrides)


def test_settings_duplicate_entities_are_rejected():
    pk = uuid4()
    with pytest.raises(ValidationError):
        _settings(entities=[pk, pk])


def test_settings_selected_mode_ignores_depth_and_direction_even_when_invalid():
    settings = _settings(selection="selected", depth=0, direction="sideways")
    assert (settings.depth, settings.direction) == (None, None)


def test_settings_component_types_are_rejected_at_systems_level():
    with pytest.raises(ValidationError):
        _settings(level="systems", entityTypes=["resource"])
    assert _settings(level="systems", entityTypes=["actor"]).entity_types == ["actor"]


def test_settings_do_not_carry_a_theme():
    settings = CustomViewSettings.model_validate(
        {
            "level": "components",
            "selection": "selected",
            "entities": [str(uuid4())],
            "theme": "dark",
        }
    )

    assert "theme" not in settings.model_dump()
