"""Environment-based configuration — `ATLAS_API_URL`/`ATLAS_PAT`
(design.md's Migration Plan step 6: "Bearer PAT via env, e.g.
`ATLAS_API_URL`/`ATLAS_PAT`"). No config file, no CLI flags: an MCP client
launches this process itself and can only pass it `command`/`args`/`env`
(see `README.md`'s client config snippet), so environment variables are the
only input surface that fits every client's own launch mechanism.
"""

import os
from dataclasses import dataclass

_ENV_API_URL = "ATLAS_API_URL"
_ENV_PAT = "ATLAS_PAT"

# The curated document this process points `FastMCP.from_openapi()` at —
# `atlas_plugin_mcp.api.schema_views.openapi_schema_view`'s own route,
# fixed by that plugin (not configurable here, since a distribution that
# selects `atlas.mcp` always mounts it at this exact path).
_OPENAPI_PATH = "/api/plugins/atlas.mcp/openapi.json"


class ConfigError(RuntimeError):
    """Raised when required environment configuration is missing or
    malformed — caught at the process entry point (`__main__.py`) and
    turned into a short, actionable stderr message instead of a traceback,
    since a misconfigured MCP client is the expected way this gets hit."""


@dataclass(frozen=True)
class Config:
    api_url: str
    """Base URL of a running Atlas backend with `atlas.mcp` selected, e.g.
    `http://localhost:8000` — no trailing slash assumed."""

    pat: str
    """An Atlas Personal Access Token, plaintext, exactly as
    `manage.py issue_pat` printed it once at issuance."""

    @property
    def openapi_url(self) -> str:
        return f"{self.api_url}{_OPENAPI_PATH}"


def load_config(env: dict[str, str] | None = None) -> Config:
    """Read `Config` from `env` (defaults to `os.environ`), raising
    `ConfigError` naming every missing variable at once rather than
    failing on the first one — a single clear message for whoever is
    debugging their MCP client's `env` block.
    """
    source = os.environ if env is None else env
    api_url = source.get(_ENV_API_URL, "").strip().rstrip("/")
    pat = source.get(_ENV_PAT, "").strip()

    missing = [
        name for name, value in ((_ENV_API_URL, api_url), (_ENV_PAT, pat)) if not value
    ]
    if missing:
        raise ConfigError(
            "Missing required environment variable(s): " + ", ".join(missing)
        )
    return Config(api_url=api_url, pat=pat)
