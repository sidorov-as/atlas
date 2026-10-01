"""`search_flow_icons` — the one MCP tool this process answers entirely on
its own, without a round-trip to Atlas (`server.py` only registers it when
the fetched OpenAPI document actually lists Flow paths, since a Flow step's
`icon` field is the only place this name set is used).

Unlike every other tool here, this isn't Atlas *data* — a Flow step's valid
`icon` values are exactly `@gravity-ui/icons`' own component names, a fixed
set that ships with the frontend (`plugins/flows/frontend/src/lib/
gravityIcons.ts`), not something any particular Atlas instance's database
holds. Answering it by calling Atlas would mean adding a new, PAT-gated
Atlas HTTP endpoint purely to proxy static npm-package metadata back out —
more moving parts for the same fixed answer every Atlas instance would give.
`atlas_mcp._gravity_icons.GRAVITY_ICONS`, a small checked-in copy synced by
`mcp/scripts/sync_gravity_icons.py`, is the source of truth instead.
"""

from ._gravity_icons import GRAVITY_ICONS

_DEFAULT_LIMIT = 20


def search_flow_icons(query: str = "", limit: int = _DEFAULT_LIMIT) -> list[str]:
    """Find `@gravity-ui/icons` component names for a Flow step's `icon`
    field. `query` is matched, word by word, against each icon's own name
    and keywords (e.g. `"error status"` matches `CircleExclamation`, whose
    keywords include "attention" and "status" — trying a couple of
    different, more generic synonyms tends to work better than one very
    literal word). An empty `query` returns the first `limit` icons in the
    package's own listed order, mainly to sanity-check the tool is
    reachable at all.
    """
    words = query.lower().split()
    matches = [
        name
        for name, blob in GRAVITY_ICONS
        if not words or any(word in blob for word in words)
    ]
    return matches[: max(limit, 0)]
