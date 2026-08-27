"""Plugin configuration schema contract tests
(`plugin-configuration-isolation` spec)."""

import pytest
from pydantic import BaseModel, ConfigDict

from atlas_plugin_api.config import (
    FileRef,
    MissingSecretEnvError,
    MissingSecretFileError,
    PluginConfigSchema,
    SecretRef,
    resolve_secrets,
)


class _ExampleConfig(PluginConfigSchema):
    issuer: str
    client_secret: str | SecretRef

    PUBLIC_FIELDS = frozenset({"issuer"})


class _NoPublicFieldsConfig(PluginConfigSchema):
    client_secret: str | SecretRef


class _FileSecretConfig(PluginConfigSchema):
    issuer: str
    key: str | FileRef

    PUBLIC_FIELDS = frozenset({"issuer"})


class _Source(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    id: str
    credential: str | SecretRef | FileRef


class _SourcesConfig(PluginConfigSchema):
    sources: list[_Source]


def test_config_rejects_unknown_fields():
    with pytest.raises(Exception, match="client_id"):
        _ExampleConfig.model_validate(
            {
                "issuer": "https://id.example.com",
                "client_secret": "literal",
                "client_id": "atlas",
            }
        )


def test_config_accepts_a_literal_secret_field():
    config = _ExampleConfig(
        issuer="https://id.example.com",
        client_secret="sekret",
    )

    assert config.client_secret == "sekret"
    assert config.has_unresolved_secrets() is False


def test_config_accepts_a_secret_ref():
    config = _ExampleConfig.model_validate(
        {
            "issuer": "https://id.example.com",
            "client_secret": {"fromEnv": "ATLAS_OIDC_CLIENT_SECRET"},
        }
    )

    assert isinstance(config.client_secret, SecretRef)
    assert config.client_secret.from_env == "ATLAS_OIDC_CLIENT_SECRET"
    assert config.has_unresolved_secrets() is True


def test_public_projection_includes_only_declared_public_fields():
    config = _ExampleConfig(
        issuer="https://id.example.com",
        client_secret="sekret",
    )

    assert config.public_projection() == {"issuer": "https://id.example.com"}


def test_public_projection_never_includes_a_secret_capable_field():
    class _Misconfigured(PluginConfigSchema):
        client_secret: str | SecretRef

        PUBLIC_FIELDS = frozenset({"client_secret"})

    config = _Misconfigured(client_secret="sekret")

    with pytest.raises(TypeError, match="secret-capable"):
        config.public_projection()


def test_public_projection_defaults_to_empty():
    config = _NoPublicFieldsConfig(client_secret="sekret")

    assert config.public_projection() == {}


def test_public_projection_rejects_an_unknown_field_name():
    class _Misconfigured(PluginConfigSchema):
        issuer: str

        PUBLIC_FIELDS = frozenset({"nonexistent"})

    config = _Misconfigured(issuer="https://id.example.com")

    with pytest.raises(TypeError, match="unknown"):
        config.public_projection()


def test_resolve_secrets_substitutes_a_fromenv_reference():
    config = _ExampleConfig.model_validate(
        {
            "issuer": "https://id.example.com",
            "client_secret": {"fromEnv": "ATLAS_OIDC_CLIENT_SECRET"},
        }
    )

    resolved = resolve_secrets(
        config,
        env={"ATLAS_OIDC_CLIENT_SECRET": "sekret-value"},
    )

    assert resolved.client_secret == "sekret-value"
    assert resolved.has_unresolved_secrets() is False


def test_resolve_secrets_leaves_a_literal_value_untouched():
    config = _ExampleConfig(
        issuer="https://id.example.com",
        client_secret="sekret",
    )

    resolved = resolve_secrets(config, env={})

    assert resolved.client_secret == "sekret"


def test_resolve_secrets_raises_when_the_env_var_is_unset():
    config = _ExampleConfig.model_validate(
        {
            "issuer": "https://id.example.com",
            "client_secret": {"fromEnv": "ATLAS_OIDC_CLIENT_SECRET"},
        }
    )

    with pytest.raises(MissingSecretEnvError) as exc_info:
        resolve_secrets(config, env={})

    assert exc_info.value.env_var == "ATLAS_OIDC_CLIENT_SECRET"


def test_resolve_secrets_never_mutates_the_original_instance():
    config = _ExampleConfig.model_validate(
        {
            "issuer": "https://id.example.com",
            "client_secret": {"fromEnv": "ATLAS_OIDC_CLIENT_SECRET"},
        }
    )

    resolve_secrets(config, env={"ATLAS_OIDC_CLIENT_SECRET": "sekret-value"})

    assert isinstance(config.client_secret, SecretRef)


def test_secret_capable_config_is_redacted_in_repr_and_safe_dump():
    config = _ExampleConfig(
        issuer="https://id.example.com", client_secret="literal-secret"
    )

    assert "literal-secret" not in repr(config)
    assert config.redacted_dump() == {
        "issuer": "https://id.example.com",
        "client_secret": "[REDACTED]",
    }


def test_validation_errors_hide_secret_bearing_input_values():
    with pytest.raises(Exception) as exc_info:
        _ExampleConfig.model_validate(
            {
                "issuer": 123,
                "client_secret": "literal-secret",
            }
        )

    assert "literal-secret" not in str(exc_info.value)


def test_config_accepts_a_file_ref():
    config = _FileSecretConfig.model_validate(
        {
            "issuer": "https://id.example.com",
            "key": {"fromFile": "/run/secrets/ssh-key"},
        }
    )

    assert isinstance(config.key, FileRef)
    assert config.key.from_file == "/run/secrets/ssh-key"
    assert config.has_unresolved_secrets() is True


def test_resolve_secrets_substitutes_a_fromfile_reference(tmp_path):
    key_path = tmp_path / "key.pem"
    key_path.write_text("-----BEGIN KEY-----\nabc\n-----END KEY-----\n")

    config = _FileSecretConfig.model_validate(
        {"issuer": "https://id.example.com", "key": {"fromFile": str(key_path)}}
    )

    resolved = resolve_secrets(config, env={})

    assert resolved.key == key_path.read_text()
    assert resolved.has_unresolved_secrets() is False


def test_resolve_secrets_raises_when_the_file_is_missing(tmp_path):
    missing_path = tmp_path / "missing.pem"

    config = _FileSecretConfig.model_validate(
        {"issuer": "https://id.example.com", "key": {"fromFile": str(missing_path)}}
    )

    with pytest.raises(MissingSecretFileError) as exc_info:
        resolve_secrets(config, env={})

    assert exc_info.value.field == "key"
    assert exc_info.value.path == str(missing_path)


def test_resolve_secrets_raises_when_the_file_is_unreadable(tmp_path):
    unreadable_dir = tmp_path / "key-dir"
    unreadable_dir.mkdir()

    config = _FileSecretConfig.model_validate(
        {"issuer": "https://id.example.com", "key": {"fromFile": str(unreadable_dir)}}
    )

    with pytest.raises(MissingSecretFileError) as exc_info:
        resolve_secrets(config, env={})

    assert exc_info.value.path == str(unreadable_dir)


def test_file_ref_capable_field_is_redacted_in_repr_and_safe_dump():
    config = _FileSecretConfig(
        issuer="https://id.example.com", key="literal-key-material"
    )

    assert "literal-key-material" not in repr(config)
    assert config.redacted_dump() == {
        "issuer": "https://id.example.com",
        "key": "[REDACTED]",
    }


def test_resolve_secrets_resolves_a_secret_ref_nested_in_a_list_of_submodels():
    config = _SourcesConfig.model_validate(
        {
            "sources": [
                {"id": "primary", "credential": {"fromEnv": "ATLAS_SOURCE_TOKEN"}},
                {"id": "secondary", "credential": "literal"},
            ]
        }
    )

    resolved = resolve_secrets(config, env={"ATLAS_SOURCE_TOKEN": "tok-value"})

    assert resolved.sources[0].credential == "tok-value"
    assert resolved.sources[1].credential == "literal"


def test_resolve_secrets_resolves_a_file_ref_nested_in_a_list_of_submodels(tmp_path):
    key_path = tmp_path / "key.pem"
    key_path.write_text("key-material")

    config = _SourcesConfig.model_validate(
        {"sources": [{"id": "primary", "credential": {"fromFile": str(key_path)}}]}
    )

    resolved = resolve_secrets(config, env={})

    assert resolved.sources[0].credential == "key-material"


def test_resolve_secrets_names_the_nested_field_for_a_missing_env_var():
    config = _SourcesConfig.model_validate(
        {
            "sources": [
                {"id": "primary", "credential": {"fromEnv": "ATLAS_SOURCE_TOKEN"}},
            ]
        }
    )

    with pytest.raises(MissingSecretEnvError) as exc_info:
        resolve_secrets(config, env={})

    assert exc_info.value.field == "sources[0].credential"
    assert exc_info.value.env_var == "ATLAS_SOURCE_TOKEN"


def test_resolve_secrets_never_mutates_the_original_nested_instance():
    config = _SourcesConfig.model_validate(
        {
            "sources": [
                {"id": "primary", "credential": {"fromEnv": "ATLAS_SOURCE_TOKEN"}},
            ]
        }
    )

    resolve_secrets(config, env={"ATLAS_SOURCE_TOKEN": "tok-value"})

    assert isinstance(config.sources[0].credential, SecretRef)
