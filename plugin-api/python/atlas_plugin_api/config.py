"""Plugin configuration schema contract (`plugin-configuration-isolation`
spec; `docs/plugin-architecture.md:475-491`).

A plugin declares its configuration as a `PluginConfigSchema` subclass — a
frozen, `extra='forbid'` Pydantic model. The composer validates a manifest's
`plugins[].config` block against it (`atlas_composer.composition`); Core
resolves it once at startup via `resolve_secrets` and hands the plugin only
its own instance (`plugin-configuration-isolation` spec: "it SHALL NOT read
global Django settings or environment variables directly").

A field that may hold a secret is typed `str | SecretRef` (or any other
literal type unioned with `SecretRef`) rather than plain `str` — the
manifest may reference an environment variable (`{fromEnv: VAR}`) instead of
a literal value for that field. A field may also be unioned with `FileRef`
(`{fromFile: <path>}`) for secret material that doesn't fit a single-line
environment variable, such as a multi-line SSH private key. Only
`resolve_secrets` ever reads the named environment variable or file; every
other consumer (the lock file, the frontend bundle, `public_projection`)
only ever sees the `SecretRef`/`FileRef` itself, never the resolved value,
which is exactly what keeps secrets out of build artifacts and the public
bootstrap response. Resolution recurses into secret references nested
inside sub-model and list-of-sub-model fields, not only top-level fields.
"""

import os
import pathlib
from collections.abc import Mapping
from typing import Any, ClassVar, get_args

from pydantic import BaseModel, ConfigDict, Field


class SecretRef(BaseModel):
    """A manifest config value naming an environment variable to resolve at
    runtime (`docs/plugin-architecture.md`'s `{fromEnv: VAR}`) — never a
    literal secret itself. Everything except `resolve_secrets` only ever
    sees this reference."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        populate_by_name=True,
        hide_input_in_errors=True,
    )

    from_env: str = Field(alias="fromEnv")


class FileRef(BaseModel):
    """A manifest config value naming a file path to read at runtime
    (`{fromFile: <path>}`) — an alternative to `SecretRef` for secret
    material that doesn't fit cleanly into a single-line environment
    variable (e.g. a multi-line SSH private key). Everything except
    `resolve_secrets` only ever sees this reference."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        populate_by_name=True,
        hide_input_in_errors=True,
    )

    from_file: str = Field(alias="fromFile")


def _is_secret_capable(annotation: Any) -> bool:
    """Whether `annotation` is `SecretRef`/`FileRef` itself, or a union that
    includes one (e.g. `str | SecretRef`) — used to reject `PUBLIC_FIELDS`
    entries that could ever hold an unresolved (or resolved) secret."""
    if annotation is SecretRef or annotation is FileRef:
        return True
    return any(_is_secret_capable(arg) for arg in get_args(annotation))


class PluginConfigSchema(BaseModel):
    """Base class for a plugin's typed, namespaced configuration schema.

    Subclasses declare their fields as ordinary Pydantic fields; a field
    that may be a secret reference is typed `<literal-type> | SecretRef`.
    `PUBLIC_FIELDS` names the subset explicitly declared safe to send to
    the frontend (`plugin-configuration-isolation` spec: "explicitly
    declared public projection") — it defaults to empty, meaning nothing is
    exposed unless a plugin opts a field in.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        populate_by_name=True,
        hide_input_in_errors=True,
    )

    PUBLIC_FIELDS: ClassVar[frozenset[str]] = frozenset()

    def __repr_args__(self):
        """Keep resolved secret-capable fields out of repr and tracebacks."""

        fields = type(self).model_fields
        return [
            (
                name,
                "[REDACTED]"
                if _is_secret_capable(fields[name].annotation)
                else getattr(self, name),
            )
            for name in fields
        ]

    def redacted_dump(self, *, by_alias: bool = True) -> dict[str, Any]:
        """Return an inspection-safe representation of provider config."""

        fields = type(self).model_fields
        return {
            str(fields[name].alias if by_alias and fields[name].alias else name): (
                "[REDACTED]"
                if _is_secret_capable(fields[name].annotation)
                else getattr(self, name)
            )
            for name in fields
        }

    def has_unresolved_secrets(self) -> bool:
        return any(
            isinstance(getattr(self, name), SecretRef | FileRef)
            for name in type(self).model_fields
        )

    def public_projection(self) -> dict[str, Any]:
        """The safe subset of this config sent to the frontend as part of
        the public bootstrap configuration response. Validated against
        `PUBLIC_FIELDS` here (not at class-definition time, since pydantic
        only finalizes `model_fields` after `__init_subclass__` runs) so a
        plugin author naming an unknown or secret-capable field fails loudly
        the first time a projection is actually built."""
        fields = type(self).model_fields
        projection: dict[str, Any] = {}
        for name in sorted(self.PUBLIC_FIELDS):
            if name not in fields:
                msg = (
                    f"{type(self).__name__}.PUBLIC_FIELDS names unknown field {name!r}"
                )
                raise TypeError(msg)
            if _is_secret_capable(fields[name].annotation):
                msg = (
                    f"{type(self).__name__}.PUBLIC_FIELDS names "
                    f"secret-capable field {name!r}"
                )
                raise TypeError(msg)
            projection[name] = getattr(self, name)
        return projection


class MissingSecretEnvError(Exception):
    """Raised by `resolve_secrets` when a config field's `fromEnv`
    reference names an environment variable that isn't set."""

    def __init__(self, field: str, env_var: str) -> None:
        super().__init__(
            f"config field {field!r} references environment variable "
            f"{env_var!r}, which is not set",
        )
        self.field = field
        self.env_var = env_var


class MissingSecretFileError(Exception):
    """Raised by `resolve_secrets` when a config field's `fromFile`
    reference names a path that doesn't exist or isn't readable."""

    def __init__(self, field: str, path: str) -> None:
        super().__init__(
            f"config field {field!r} references file {path!r}, "
            "which does not exist or is not readable",
        )
        self.field = field
        self.path = path


def _resolve_value(path: str, value: Any, resolved_env: Mapping[str, str]) -> Any:
    """Resolve `value` (a field or list-item value found at dotted/indexed
    `path`), recursing into nested `BaseModel` and `list` values so a
    `SecretRef`/`FileRef` nested arbitrarily deep inside sub-model or list
    fields is resolved, not only ones at the top level of a
    `PluginConfigSchema`."""
    if isinstance(value, SecretRef):
        if value.from_env not in resolved_env:
            raise MissingSecretEnvError(path, value.from_env)
        return resolved_env[value.from_env]
    if isinstance(value, FileRef):
        try:
            return pathlib.Path(value.from_file).read_text()
        except OSError as exc:
            raise MissingSecretFileError(path, value.from_file) from exc
    if isinstance(value, BaseModel):
        nested = {
            name: _resolve_value(f"{path}.{name}", getattr(value, name), resolved_env)
            for name in type(value).model_fields
        }
        return type(value).model_validate(nested)
    if isinstance(value, list):
        return [
            _resolve_value(f"{path}[{index}]", item, resolved_env)
            for index, item in enumerate(value)
        ]
    return value


def resolve_secrets(
    config: PluginConfigSchema,
    *,
    env: Mapping[str, str] | None = None,
) -> PluginConfigSchema:
    """The central secret-resolution step
    (`plugin-configuration-isolation` spec: "Secrets are resolved centrally
    and never exposed"). Returns a new instance of `config`'s own schema
    with every `SecretRef` field replaced by the named environment
    variable's value and every `FileRef` field replaced by the named file's
    contents, resolved against `env` (defaults to `os.environ`).
    Resolution recurses into nested `BaseModel` and `list` fields, so a
    secret reference nested inside a sub-model or a list of sub-models is
    resolved too, not only top-level fields. Never mutates `config` or
    writes the resolved value anywhere but the returned instance — callers
    must not serialize it back into the manifest, the lock file, or any
    frontend-visible artifact."""
    resolved_env = os.environ if env is None else env
    resolved: dict[str, Any] = {
        name: _resolve_value(name, getattr(config, name), resolved_env)
        for name in type(config).model_fields
    }
    return type(config).model_validate(resolved)


_resolved_plugin_configs: dict[str, PluginConfigSchema] = {}


def bind_plugin_config(
    plugin_id: str, config: PluginConfigSchema, *, owner: str
) -> None:
    """Bind one Core-resolved config for its owning runtime plugin."""

    existing = _resolved_plugin_configs.get(plugin_id)
    if existing is not None and existing != config:
        raise ValueError(
            f"plugin config {plugin_id!r} is already bound by another value"
        )
    _resolved_plugin_configs[plugin_id] = config


def get_plugin_config[ConfigT: PluginConfigSchema](
    plugin_id: str, schema: type[ConfigT]
) -> ConfigT:
    """Return the resolved config only through its declared schema."""

    value = _resolved_plugin_configs.get(plugin_id)
    if value is None:
        raise LookupError(f"no resolved {schema.__name__} for plugin {plugin_id!r}")
    if not isinstance(value, schema):
        raise TypeError(
            f"resolved config for plugin {plugin_id!r} is not {schema.__name__}"
        )
    return value
