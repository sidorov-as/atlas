# Missing tools and scopes

## Flow tools

Required: `list_flows`, `get_flow`, `create_flow`, `update_flow`.
Used when present: `validate_flow`, `search_flow_icons`, `search_api_endpoints`, `search_api_operations`.

| Situation                           | Do                                                                                                                                              |
|-------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------|
| No flow tools at all                | Stop. Say flows are not available on this Atlas (the flows plugin is not installed or exposed through MCP) and do nothing further.              |
| A required flow tool is missing     | Stop and name the tool.                                                                                                                         |
| `validate_flow` missing             | Say the server cannot pre-check the flow; validate it yourself and expect errors at save time. Continue.                                        |
| `search_flow_icons` missing         | Leave `icon` out of every step. Tell the user once.                                                                                             |
| Endpoint or operation tools missing | Say you cannot bind to specific endpoints or operations; bind to the owning entity or use plain or external steps. Continue if the user agrees. |

## Scopes

- Reading flows and `validate_flow` need `flows:read`.
- Creating and updating flows needs `flows:write`.
- Searching the catalog needs `catalog:read`.
- Flows do not need `apis:write`. That scope is for `atlas-curator`'s endpoint and operation link tools
  (`link_endpoint_consumers`, `unlink_endpoint_consumers`, `link_operation_participants`,
  `unlink_operation_participants`), which `atlas-flow` never calls.

When a flow write is rejected for a permission or scope reason, report that flow writes need the `flows:write`
scope (or that the user lacks edit permission on the system), tell the user how to fix the token, and do not retry
the same request.
