"""Atlas MCP transport — a standalone stdio MCP server bridging an MCP
client (Claude Desktop, Codex, Qwen, etc.) to the `atlas.mcp` plugin's
curated HTTP API.

Deliberately outside `plugins/`, `composer`, and every distribution
(design.md Decision 7: "The MCP transport process itself lives outside
composer entirely") — it holds no Django import at all (Decision 1) and is
built, deployed, and released on its own schedule, independent of which
Atlas distribution it talks to. See this directory's own `README.md` for
how to build, run, and connect an MCP client to it.
"""
