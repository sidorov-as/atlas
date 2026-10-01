# Shared rules for all Atlas skills

Every Atlas skill (`atlas-curator`, `atlas-scout`, `atlas-flow`) follows these rules. They are
kept here once so they cannot drift between skills. Read this file before the first catalog
read or write.

## 1. MCP preflight

Before any catalog read or write, find out which Atlas MCP tools are available in this
session. Do not assume; the tool list depends on the server version and installed plugins.

| Need                         | Tools                                                                                                                                      |
|------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------|
| Required for any entity work | `search_catalog`, `get_entity`, `create_entity`, `update_entity`                                                                           |
| Preferred for entity work    | `describe_kinds` (field and enum truth), `create_relationship`, `list_relationships`, `dryRun` support on write tools (accurate summaries) |
| Flow work                    | `list_flows`, `get_flow`, `create_flow`, `update_flow`, `search_flow_icons`, `validate_flow`                                               |
| Flow steps bound to APIs     | `search_api_endpoints`, `search_api_operations`                                                                                            |

Then act on what is found:

- **No Atlas catalog tools at all.** Stop. Tell the user the Atlas MCP server is not
  connected and point them to the skills page of the documentation site (it explains the
  server connection and the token). Make no write attempt.
- **A required tool is missing.** Stop and name the tool.
- **A preferred tool is missing.** Say what you cannot do (for example: "I can create the
  services but not their relationships"), and continue with reduced behavior only if the
  user agrees.
- **`atlas-scout` or `atlas-flow` cannot find `atlas-curator`.** Stop and tell the user to
  install the full set of skills; do not continue without it.

Token scopes: entity writes need `catalog:write`; flow writes need `flows:write`. A write
rejected for a missing scope or permission is a connection problem. Report which scope is
needed and do not retry the same request.

## 2. Language

If the user asks for a specific language, conduct all later discussion, plans, and
summaries in it. Before drafting any titles or descriptions, ask once which language to
write them in, and use that answer for everything written in this session. Entity `name`
identifiers, field names, and enum values stay in English because the server requires it.

## 3. Confirmation before writing

Show a summary in the conversation of exactly what will be created or changed, and wait
for explicit confirmation before the first write. When the server supports `dryRun`, build
the summary from the dry-run response rather than from your own prediction. One summary per
batch is enough; offer to expand any item. A plan file on disk is produced only if the user
asks for one.

## 4. No removal

Never call `remove_entity`, `purge_entity`, or `delete_flow`, even when asked. When the
user asks to remove or delete an entity or a flow, make no removal call, explain that
removal is done in the Atlas web UI (where removed entities can be restored), and offer to
list the related entities you can find with the search tools.

Catalog items with no counterpart in the code or conversation are reported as
`investigate` and left alone.

The one deletion a skill may perform is `delete_relationship` for a manual relationship,
only when the user explicitly asks for that specific relationship to be deleted and has
confirmed a dry-run summary of the deletion.
