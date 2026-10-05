"""Process-wide runtime state of the search plugin.

Populated by `plugin.register_runtime()` / `plugin.finalize_runtime()`. A
plugin that is not selected or is disabled never runs those hooks, so
`is_active()` stays false and everything else in the plugin stays inert.
"""

from dataclasses import dataclass

from atlas_plugin_api import SearchEngine

from .config import SearchPluginConfig


@dataclass
class _State:
    config: SearchPluginConfig | None = None
    engine: SearchEngine | None = None


_state = _State()


def configure(config: SearchPluginConfig) -> None:
    _state.config = config


def bind_engine(engine: SearchEngine) -> None:
    _state.engine = engine


def reset() -> None:
    _state.config = None
    _state.engine = None


def is_active() -> bool:
    """True once startup finished: config bound and an engine selected."""
    return _state.config is not None and _state.engine is not None


def get_config() -> SearchPluginConfig:
    if _state.config is None:
        raise RuntimeError("the search plugin is not active")
    return _state.config


def get_engine() -> SearchEngine:
    if _state.engine is None:
        raise RuntimeError("the search plugin has no engine; it is not active")
    return _state.engine
