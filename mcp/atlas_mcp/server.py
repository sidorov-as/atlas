"""Builds the `FastMCP` server that bridges an MCP client to Atlas's
curated MCP HTTP API (`atlas.mcp` plugin).

Holds no Django import at all (design.md Decision 1: "the MCP transport
process holds no Django import ... calls a new, curated Atlas HTTP API over
`httpx`") — every tool this process exposes is generated straight from the
curated OpenAPI document `atlas.mcp` serves at `Config.openapi_url`
(`atlas_plugin_mcp.api.schema_views`), via `FastMCP.from_openapi()`
(design.md Decision 2 / the Flagsmith precedent it cites). No tool is
hand-written here, so this process can never drift from what that document
currently lists — e.g. Flow tools appear or disappear automatically as
`atlas.flows` is selected in, or excluded from, the distribution this
process points at.

Uses `httpx2` exclusively, not plain `httpx`: `FastMCP.from_openapi()`
vendors its own fork of `httpx` for the client it hands generated tools
(a plain `httpx.AsyncClient` still works, but only via a deprecated
compatibility path fastmcp warns will be removed) — `httpx2`'s public API
otherwise mirrors `httpx`'s exactly, so the one-off sync fetch below uses it
too rather than pulling in `httpx` as a second, otherwise-unneeded
dependency.
"""

import httpx2
from fastmcp import FastMCP

from .config import Config
from .icons import search_flow_icons

_REQUEST_TIMEOUT_SECONDS = 30.0

_BASE_INSTRUCTIONS = """\
Atlas is this organization's own internal software catalog: its systems,
components, resources, and APIs, their ownership, and how they depend on
each other. Reach for these tools whenever a question is about *this
organization's own* services or architecture — e.g. "what does <service>
depend on", "who owns <system>", "what components make up <system>" — that
information lives only in Atlas, never in general knowledge, so don't guess
or answer from training data alone.

Start broad with search_catalog (free-text query, kind, owner, tags), then
call get_entity for one result's full detail and spec."""

_AUTHORING_INSTRUCTIONS = """\

Writing to the catalog (create_entity, update_entity, and the relationship
tools list_relationships/create_relationship/update_relationship/
delete_relationship): call describe_kinds first to see which `spec` fields,
enum values, and required fields each kind accepts instead of guessing them.
Unknown or misspelled `spec`/`metadata` keys are rejected, never silently
ignored, so read the error and fix the key. `relationships` is not part of an
entity's `spec`: link entities with create_relationship (manual relationships
only; ones with origin `yaml` come from ingested manifests and cannot be
changed here). Before any write the user hasn't already seen exactly, repeat
it with `dryRun` true, show the user the returned `changes` and `warnings`,
and only then repeat it without `dryRun`. A dry-run saves nothing."""

_FLOW_INSTRUCTIONS = """\

Flow tools (list_flows, get_flow, and — with the right PAT scope —
create_flow/update_flow/delete_flow) describe multi-step business or
operational processes that cross several catalog entities, e.g. how a
booking or a payment moves through several components end to end. Use
list_flows/get_flow the same way search_catalog/get_entity are used for
entities. Before writing a step's `icon` field, call search_flow_icons to
find a real @gravity-ui/icons component name for it — icon values aren't
validated, so a guessed or made-up name silently renders as no icon at all.
While drafting a flow, call validate_flow with the body (and `flowId` when
replacing an existing flow): it lists every rule violation at once without
saving, so fix them together; then use `dryRun` on create_flow/update_flow
to confirm."""

_API_INSTRUCTIONS = """\

API endpoint/operation tools (search_api_endpoints, get_api_endpoint,
get_endpoint_consumers, and their search_api_operations/get_api_operation/
get_operation_consumers counterparts for async channels) go one level below
an `api` entity: its individual HTTP endpoints and messaging operations.
For "which services use this endpoint/operation", call
get_endpoint_consumers/get_operation_consumers with its id — they return the
Services explicitly linked to that exact endpoint or operation. Don't answer
from a component's API-wide `consumesApi` relation instead: that only says a
Service uses the API as a whole, and Atlas does track usage at the finer
endpoint/operation level."""

_API_USAGE_INSTRUCTIONS = """\

Linking services to endpoints/operations (link_endpoint_consumers,
unlink_endpoint_consumers, link_operation_participants,
unlink_operation_participants; need the `apis:write` scope) takes one Service
(a component) and a list of items per call, up to 200. Send one call per
Service, not one per link. Name each target by id when you already hold it from
a search, or by natural key when you only know it from code: `api`, `method`,
`path` for an endpoint; `api`, `channelAddress`, `direction` for an operation,
which also needs a `role`. Give exactly one form per item. The call succeeds
partially: read the per-item `status`, report `not_found`, `ambiguous` and
`conflict` items to the user instead of guessing a replacement, and rerun
safely, since repeats come back `unchanged`. Linking an endpoint can also add
the API to the Service's `consumesAPI`; unlinking never removes it. Before
removing links, repeat the call with `dryRun` true and show the user what would
go."""


def _auth_headers(pat: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {pat}"}


def _fetch_openapi_spec(config: Config) -> dict:
    """A one-off, synchronous fetch at startup — this process rebuilds its
    tool list only when restarted, matching how an MCP client itself only
    (re)reads a server's tool list once per session/connection; nothing
    here polls for tool-list changes at runtime.
    """
    response = httpx2.get(
        config.openapi_url,
        headers=_auth_headers(config.pat),
        timeout=_REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


def _has_flow_tools(openapi_spec: dict) -> bool:
    """Same condition the fetched document itself already encodes (`atlas_
    plugin_mcp.api.urls.build_router()`'s own `atlas.flows`-installed
    check) — re-derived from its `paths` here rather than asking Atlas
    again, since this process already has the document in hand.
    """
    return any("/flows/" in path for path in openapi_spec.get("paths", {}))


def _has_api_tools(openapi_spec: dict) -> bool:
    """Same re-derivation from `paths` as `_has_flow_tools`, for the
    `atlas.apis`-gated tools: their consumers routes exist only then."""
    return any("/consumers/" in path for path in openapi_spec.get("paths", {}))


def _has_api_usage_tools(openapi_spec: dict) -> bool:
    """The link/unlink routes, present only with `atlas.apis` too."""
    return any(
        path.endswith(("/consumers/link/", "/participants/link/"))
        for path in openapi_spec.get("paths", {})
    )


def build_server(config: Config) -> FastMCP:
    openapi_spec = _fetch_openapi_spec(config)
    has_flow_tools = _has_flow_tools(openapi_spec)

    instructions = _BASE_INSTRUCTIONS + _AUTHORING_INSTRUCTIONS
    if has_flow_tools:
        instructions += _FLOW_INSTRUCTIONS
    if _has_api_tools(openapi_spec):
        instructions += _API_INSTRUCTIONS
    if _has_api_usage_tools(openapi_spec):
        instructions += _API_USAGE_INSTRUCTIONS

    # This client — not the one-off request `_fetch_openapi_spec` made
    # above — is what every generated tool actually calls through; it
    # outlives server startup, carrying the same Bearer PAT on every
    # request.
    client = httpx2.AsyncClient(
        base_url=config.api_url,
        headers=_auth_headers(config.pat),
        timeout=_REQUEST_TIMEOUT_SECONDS,
    )

    mcp_server = FastMCP.from_openapi(
        openapi_spec=openapi_spec,
        client=client,
        name="Atlas",
        instructions=instructions,
    )

    if has_flow_tools:
        # Unlike every other tool here, this one is answered entirely by
        # this process itself, with no Atlas HTTP call — see icons.py's
        # module docstring for why. Gated on `has_flow_tools` because a
        # Flow step's `icon` field is the only place this name set is
        # used; a distribution without `atlas.flows` has nothing for it to
        # validate against.
        mcp_server.tool(search_flow_icons)

    return mcp_server
