import pytest
from c4.renderers.plantuml import RemotePlantUMLBackend
from pydantic import ValidationError

from atlas_plugin_c4 import c4
from atlas_plugin_c4.config import C4PluginConfig


def test_defaults_to_local_renderer(monkeypatch):
    # The real backend refuses to construct without a PlantUML executable,
    # which CI does not install; only the selection and arguments matter here.
    created = []
    monkeypatch.setattr(
        c4, "LocalPlantUMLBackend", lambda **kwargs: created.append(kwargs)
    )
    config = C4PluginConfig()
    assert config.renderer == "local"
    c4._plantuml_backend(config)
    assert created == [
        {"timeout_seconds": 30.0, "plantuml_args": ["-DRELATIVE_INCLUDE=."]}
    ]


def test_remote_renderer_uses_configured_server():
    config = C4PluginConfig.model_validate(
        {"renderer": "remote", "serverUrl": "https://plantuml.example.com/"}
    )
    backend = c4._plantuml_backend(config)
    assert isinstance(backend, RemotePlantUMLBackend)
    assert backend._server_url == "https://plantuml.example.com"


def test_remote_renderer_without_url_uses_library_default():
    backend = c4._plantuml_backend(C4PluginConfig(renderer="remote"))
    assert isinstance(backend, RemotePlantUMLBackend)


@pytest.mark.parametrize(
    "raw",
    [
        {"serverUrl": "https://plantuml.example.com"},
        {"renderer": "remote", "serverUrl": "ftp://plantuml.example.com"},
        {"renderer": "remote", "serverUrl": "https://u:p@plantuml.example.com"},
        {"renderer": "remote", "unknown": 1},
        {"renderer": "cloud"},
    ],
)
def test_invalid_config_is_rejected(raw):
    with pytest.raises(ValidationError):
        C4PluginConfig.model_validate(raw)
