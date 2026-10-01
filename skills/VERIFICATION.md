# Manual verification checklist

CI checks the skills' structure (`scripts/check_skills.py`: frontmatter and file references). It cannot check
behavior, because a skill is model instructions and its output is not deterministic. A maintainer runs this
checklist by hand. The invariants do not depend on a particular repository, so no sample repository or expected
output is kept.

## When to run it

- Before releasing a change to anything under `skills/`.
- Whenever the MCP surface changes (a tool or field is renamed, added, or removed). CI does not catch tool
  renames, so this is the only check for them.

## Setup

- A local Atlas with the demo catalog (`make dev-up`, then `make seed-demo`), the `atlas.mcp`, `atlas.flows`, and
  `atlas.apis` plugins selected, and the MCP transport connected to your assistant (see
  [mcp/README.md](../mcp/README.md)).
- A token with `catalog:read`, `catalog:write`, `flows:read`, and `flows:write` (`make issue-pat`).
- The three skills installed together in the assistant.
- Any small repository for `atlas-scout` (a few services and a database is enough).

Run the checks per skill as shown, then run the reduced-capability pass at the end.

## Invariants

Tick each one per skill it applies to. A failure is a bug in the skill text; fix it and run again.

| #  | Invariant                                                                                                                                                                                                                                                                                         |    `atlas-scout`    | `atlas-curator` | `atlas-flow` |
|----|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:-------------------:|:---------------:|:------------:|
| 1  | **Nothing is written before confirmation.** Watch the MCP tool calls: until you confirm the summary there is no `create_*`, `update_*`, or relationship write, and no non-`dryRun` call.                                                                                                          | x (it never writes) |        x        |      x       |
| 2  | **A second run creates no duplicates.** Apply the same approved plan or flow request twice. The second run reports every item as unchanged (flows: updates the existing flow instead of creating a second one) and the catalog count of each kind is the same.                                    |          x          |        x        |      x       |
| 3  | **Every proposed entity cites a file and line.** Each item in the plan has a `path:line` that exists and supports it.                                                                                                                                                                             |          x          |                 |              |
| 4  | **Ambiguous cases become questions.** In the test repository include a unit that could be a service or a worker; the skill marks it uncertain and asks, one question at a time, with a recommendation and its evidence.                                                                           |          x          |                 |              |
| 5  | **No cosmetic questions.** It never asks for titles, descriptions, or tags.                                                                                                                                                                                                                       |          x          |                 |              |
| 6  | **Language rule.** Ask for a non-English language. Questions, plans, and summaries are in it; titles and descriptions use the language you chose when asked once; `name` identifiers, field names, and enum values stay English.                                                                  |          x          |        x        |      x       |
| 7  | **No removal.** Ask it to delete an entity (and, for flows, a flow). No `remove_entity`, `purge_entity`, or `delete_flow` call is made; it explains that removal is done in the Atlas web UI. An entity in the catalog with no counterpart in the code appears as `investigate` and is untouched. |          x          |        x        |      x       |
| 8  | **Owner from an existing group.** Name a group that does not exist. The skill stops and tells you to create it; it assigns no other group.                                                                                                                                                        |          x          |        x        |              |
| 9  | **Order and list fields.** In a plan with a system and its components, the system is created first. Adding a second dependency to a component that already has one leaves both in `dependsOn`.                                                                                                    |                     |        x        |              |
| 10 | **API spec is verified.** Attach an OpenAPI file. The skill reports the number of endpoints found, or the failure flag. A spec over 2 MiB is not sent inline.                                                                                                                                     |                     |        x        |              |
| 11 | **Relationships have a label and interaction kind**, and an existing equivalent relationship is reported unchanged, not duplicated. A `yaml`-origin relationship is not modified.                                                                                                                 |                     |        x        |              |
| 12 | **Home system first, then steps.** The flow's system is established before steps are drafted; a branch becomes labeled transitions; a cycle is reported (with the steps involved) before saving.                                                                                                  |                     |                 |      x       |
| 13 | **Binding.** A step for an existing component references it; a call to a documented endpoint references the endpoint; an unknown party becomes an external step and is listed in the summary before saving, with an offer to document it afterward.                                               |                     |                 |      x       |
| 14 | **Editing keeps steps.** Add a step to an existing flow; the saved list contains every previous step plus the new one. Re-binding an external step changes only that step.                                                                                                                        |                     |                 |      x       |
| 15 | **Icons are real.** Any icon set on a step came from `search_flow_icons`.                                                                                                                                                                                                                         |                     |                 |      x       |

## Reduced-capability pass

Repeat a short run against an MCP server that lacks the newer tools. Easiest: connect the transport to an Atlas
built without `atlas.flows`, or with an older `atlas.mcp`, or temporarily connect nothing.

| Situation                                         | Expected                                                                                       |
|---------------------------------------------------|------------------------------------------------------------------------------------------------|
| No Atlas tools connected                          | Each skill stops, explains how to connect the MCP server, and attempts no write                |
| No relationship tools                             | The skill says relationships cannot be created and asks whether to continue with entities only |
| No `describe_kinds`                               | The curator says its bundled reference may be out of date and continues                        |
| No `dryRun` support                               | The summary is built by the skill, and the skill says so                                       |
| No flow tools                                     | `atlas-flow` says flows are not available on this Atlas and does nothing further               |
| Token without `catalog:write` or `flows:write`    | The skill reports which scope is needed and does not retry                                     |
| `atlas-curator` removed from the skills directory | `atlas-scout` and `atlas-flow` stop and tell you to install the full set                       |

## Record

Note the date, the Atlas version, the assistant and model used, and any invariant that failed, in the pull request
that changes the skills.
