---
title: Catalog authoring skills
description: Install the Atlas skills that let an AI assistant survey a codebase, write catalog entities, and build flows through the MCP server.
audience: [ catalog-user, operator ]
page-type: task
---

# Catalog authoring skills

The Atlas MCP server gives an assistant tools to read and write the catalog,
but a tool list does not say which fields a Component needs, in what order
linked entities must be created, or that nothing should be written before you
agree. The skills in the repository's [`skills/`](https://github.com/sidorov-as/atlas/tree/main/skills)
directory carry that know-how. Use them to fill the catalog from a codebase or
to describe a process in conversation and save it as a flow.

## The three skills

| Skill           | Use it to                                                                                                                                                | Writes                                     |
|-----------------|----------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------|
| `atlas-scout`   | Survey a repository, propose systems, components, resources, APIs and relationships, interview you on structural decisions, and produce an approved plan | Nothing; hands the plan to `atlas-curator` |
| `atlas-flow`    | Describe a process and save it as a flow whose steps are bound to catalog entities and API endpoints or operations                                       | Flows                                      |
| `atlas-curator` | Create or update Systems, Components, Resources, APIs, and relationships, in the right order and without duplicates                                      | Entities and relationships                 |

`atlas-curator` is the only skill that writes entities. `atlas-scout` and
`atlas-flow` rely on it, so **install the three skills together**. If either
of them cannot find `atlas-curator`, it stops and asks you to install the full
set.

## Prerequisites

- A running Atlas with the [`atlas.mcp` plugin](mcp.md) selected. Flow
  features also need `atlas.flows`; endpoint and operation binding needs
  `atlas.apis`.
- The [MCP transport process](mcp.md#mcp-transport-process) connected to your
  assistant (see [`mcp/README.md`](https://github.com/sidorov-as/atlas/tree/main/mcp)
  for client configuration).
- A [Personal Access Token](mcp.md#issuing-a-token) with the scopes the work
  needs:

| Work                                        | Scopes                          |
|---------------------------------------------|---------------------------------|
| Survey and plan only                        | `catalog:read`                  |
| Create or update entities and relationships | `catalog:read`, `catalog:write` |
| Read flows and validate a flow              | `flows:read`                    |
| Create or update flows                      | `flows:write`                   |

A write rejected for a missing scope is reported by the skill and not
retried; issue a token with the scope and restart the transport process.

## Install

### With `npx skills` (recommended)

[`npx skills`](https://github.com/vercel-labs/skills) installs the skills from
the repository into the folder each assistant reads. Install all three
together:

```shell
npx skills add sidorov-as/atlas --skill atlas-scout atlas-flow atlas-curator
```

It asks which assistants to install for and whether to install for the current
project or for all your projects. To skip the questions, name the assistant and
scope:

```shell
# Claude Code, current project
npx skills add sidorov-as/atlas --skill atlas-scout atlas-flow atlas-curator -a claude-code -y

# Codex, all projects
npx skills add sidorov-as/atlas --skill atlas-scout atlas-flow atlas-curator -a codex -g -y
```

Update later with `npx skills update` and remove with `npx skills remove`.

### Manual copy

Copy the three folders into your assistant's skills directory, side by side.
For Claude Code, for all your projects:

```shell
# from the root of the Atlas repository
mkdir -p ~/.claude/skills
cp -R skills/atlas-scout skills/atlas-flow skills/atlas-curator ~/.claude/skills/
```

To use them in one project only, copy them into `.claude/skills/` in that
project. Other assistants that read `SKILL.md` folders use their own skills
directory the same way.

### Verify

To verify, start a session with the MCP server connected and ask for
something a skill covers, for example "document this repository in Atlas". The
skill begins by checking which Atlas tools are available.

## What every skill does

- **Checks the server first.** If no Atlas tools are connected it stops and
  explains how to connect. If a tool it prefers is missing (for example the
  relationship tools on an older server) it says what it cannot do and
  continues only if you agree.
- **Writes nothing without your confirmation.** It shows a summary in the
  conversation of what will be created or changed. When the server supports
  [`dryRun`](mcp.md#previewing-a-write-with-dryrun), the summary comes from the
  server's own preview.
- **Never removes anything.** No skill removes, purges, or restores an
  entity, or deletes a flow, even if asked. Removal is done in the Atlas web
  UI, where removed entities can be restored. Entities that exist in the
  catalog but not in the code are listed as "investigate" and left alone. The
  one exception is deleting a manual relationship you explicitly ask for, after
  you confirm.
- **Uses existing groups as owners.** Groups cannot be created over MCP. If
  the group you want does not exist, the skill stops and asks you to create it
  in Atlas.

## Language

Ask the assistant to respond in a language and the skill conducts the whole
conversation, plans, and summaries in it. Before writing, the skill asks once
which language to use for entity titles and descriptions and applies it to
everything it writes. Entity `name` identifiers, field names, and enum values
stay in English because the server requires them.

## Worked example

You point the assistant at a repository and say "document this in Atlas".
This is an illustration of the flow, not recorded output.

1. `atlas-scout` confirms the scope, reads the code, and checks the catalog.
2. It asks one question at a time, each with a recommendation and its
   evidence, for example: "`services/billing` and `web` look like one system
   named `payments`. Recommended: one system, because both are built from the
   same repository (`docker-compose.yml:3`). Agree?"
3. It shows a plan listing each entity and relationship as `new`, `update`,
   `unchanged`, or `investigate`, with a file and line for each.
4. After you approve the plan, `atlas-curator` takes over, shows a change
   summary built from `dryRun`, and writes only after you confirm: systems,
   then resources and APIs, then components, then relationships.
5. Afterwards you ask `atlas-flow` to "describe the checkout process". It asks
   for the home system, walks through the steps and branches, binds steps to the
   components and endpoints that now exist, shows the flow for confirmation,
   and saves it.

Running the same plan again creates no duplicates: the curator searches the
catalog by kind and name before each create and reports matches as unchanged.

## When something goes wrong

| Symptom                                                                     | What it means                                      | What to do                                                                             |
|-----------------------------------------------------------------------------|----------------------------------------------------|----------------------------------------------------------------------------------------|
| The skill says no Atlas tools are connected                                 | The MCP server is not connected to the assistant   | Follow [MCP transport process](mcp.md#mcp-transport-process) and restart the assistant |
| The skill says it cannot create relationships, or has no kind introspection | The server is older than the skills expect         | Upgrade Atlas, or continue at reduced capability when the skill asks                   |
| The skill says flows are not available                                      | `atlas.flows` is not selected in your distribution | Select the plugin and rebuild, see [MCP](mcp.md#limits-and-troubleshooting)            |
| A write is rejected for a scope                                             | The token lacks `catalog:write` or `flows:write`   | Issue a token with the scope                                                           |
| The skill stops at the owner                                                | The group you named does not exist                 | Create the group in Atlas, then continue                                               |
| An API shows no endpoints                                                   | No spec was attached, or its fetch or parse failed | Attach the spec; the curator reports the failure flags after writing                   |

## Next steps

See [MCP](mcp.md) for the tool set, scopes, and token management,
[Flows](flows.md) for the flow model, and [APIs](apis.md) for how specs
become endpoints and operations.
