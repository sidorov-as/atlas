"""Process entry point — `python -m atlas_mcp` (also installed as the
`atlas-mcp` console script; see `README.md`'s MCP-client config snippet,
which invokes it that way).

Speaks stdio, never HTTP, to the MCP client that launched it (design.md:
"a stdio-speaking bridge to the new curated API") — the client owns this
process's stdin/stdout entirely, so a configuration error is reported on
stderr and a non-zero exit, never printed to stdout where it would corrupt
the MCP wire protocol.
"""

import sys

from .config import ConfigError, load_config
from .server import build_server


def main() -> None:
    try:
        config = load_config()
    except ConfigError as exc:
        print(f"atlas-mcp: {exc}", file=sys.stderr)
        raise SystemExit(1) from None

    build_server(config).run(transport="stdio")


if __name__ == "__main__":
    main()
