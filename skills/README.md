# Atlas skills

Skills are instructions an AI assistant loads on demand. These three turn the Atlas MCP
server's tools into correct, reviewable catalog changes. Each skill is a folder with a
`SKILL.md` (name, trigger description, workflow) and a `references/` folder loaded only
when needed.

| Skill                                     | Use it to                                                                                                       | Writes                                     |
|-------------------------------------------|-----------------------------------------------------------------------------------------------------------------|--------------------------------------------|
| [`atlas-scout`](atlas-scout/SKILL.md)     | Survey a codebase, propose a catalog model, interview you on structural decisions, and produce an approved plan | Nothing; hands the plan to `atlas-curator` |
| [`atlas-flow`](atlas-flow/SKILL.md)       | Describe a process in conversation and save it as a flow bound to catalog entities and endpoints                | Flows                                      |
| [`atlas-curator`](atlas-curator/SKILL.md) | Create or update Systems, Components, Resources, APIs, and relationships                                        | Entities, relationships, and endpoint/operation links |

## How they relate

`atlas-curator` is the only skill that writes entities. `atlas-scout` ends with a plan
that it hands to the curator. `atlas-flow` writes flows itself, and when a step involves
an entity missing from the catalog it offers to hand a one-entity plan to the curator.
The shared rules (MCP preflight, language, confirmation before writes, no removal) live in
[`atlas-curator/references/shared-rules.md`](atlas-curator/references/shared-rules.md).

**Install the three skills together.** `atlas-scout` and `atlas-flow` refer to the
curator's files and stop if it is missing.

## Requirements

- The [Atlas MCP server](../mcp/README.md) connected to your assistant.
- A Personal Access Token with `catalog:read` and `catalog:write` for entity work, plus
  `flows:read` and `flows:write` for flows, and `apis:write` to link Services to API endpoints and
  operations.
- The `mcp-authoring-tools` tools (`describe_kinds`, relationship tools, `dryRun`) are
  preferred. Against an older server the skills say what they cannot do and continue at
  reduced capability only if you agree.

## Installation

### With `npx skills` (recommended)

[`npx skills`](https://github.com/vercel-labs/skills) installs the skills straight from the repository, into the
folder each assistant reads. Install all three together:

```shell
npx skills add sidorov-as/atlas --skill atlas-scout atlas-flow atlas-curator
```

It asks which assistants to install for and whether to install for the current project or for all your projects.
To skip the questions, name the assistant and scope:

```shell
# Claude Code, current project
npx skills add sidorov-as/atlas --skill atlas-scout atlas-flow atlas-curator -a claude-code -y

# Codex, all projects
npx skills add sidorov-as/atlas --skill atlas-scout atlas-flow atlas-curator -a codex -g -y
```

List what is available without installing (`--list`), update later with `npx skills update`, and remove with
`npx skills remove`. Add `--copy` to copy the files instead of linking them.

### Manual copy

Copy the three folders into your assistant's skills directory, keeping them side by side.

Claude Code (all projects):

```shell
mkdir -p ~/.claude/skills
cp -R skills/atlas-scout skills/atlas-flow skills/atlas-curator ~/.claude/skills/
```

For one project, copy them into `.claude/skills/` in that project instead. Other
assistants that support the `SKILL.md` format: use their skills directory the same way.

## Checks

`scripts/check_skills.py` runs in CI and verifies each `SKILL.md` frontmatter and every relative
reference. Behavior is verified by hand with [VERIFICATION.md](VERIFICATION.md).
