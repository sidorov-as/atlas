---
name: atlas-scout
description: Surveys a codebase and proposes an Atlas catalog model (systems, components, resources, APIs, relationships), interviews the user on structural decisions, and hands an approved plan to atlas-curator. Use when the user points at a repository or directory and asks to document it, map its architecture, or fill the Atlas catalog from code.
---

# Atlas Scout

Turns a codebase into an approved catalog plan.

## When to use

The user points at a repository or directory and wants its architecture mapped into Atlas: "document this repo",
"fill the catalog from this code", "what systems and services are in here". This skill reads and plans; it
**never creates entities**. Writing is done by `atlas-curator` after the user approves the plan.

Check that `atlas-curator` is available (see the shared rules) before starting. If it is not, stop.

## Rules of conduct

- Survey first, ask later. Form the candidate model from the code before the first question.
- One question at a time, each with a recommended answer and its evidence (see
  [references/interview.md](references/interview.md)).
- Ask only structural questions. Draft titles, descriptions, and tags yourself; never ask about them.
- Every candidate cites evidence: a file path and line. A candidate without evidence is not proposed.
- Do not silently choose. When the code does not settle something (service or worker? one system or two?), mark
  it uncertain and ask.
- Never propose removing anything. Catalog entities with no counterpart in the code are `investigate`.
- Read-only on the repository. Do not edit the user's code.

## Workflow

### 1. Locate

Preflight (shared rules). Confirm the scope with the user: which directory, and for a monorepo with several
independently deployable units, whether to cover the whole repository or one subdirectory. Do not start the survey
until the scope is confirmed.

### 2. Survey

Read the code and build the candidate model using [references/discovery.md](references/discovery.md): systems,
Components (with type), Resources (with type), APIs (with spec files when present), and relationships (calls
between components, data access, messaging). Treat a library, a deployable service, a web frontend, and a
background worker as distinct. Map data stores and message brokers to Resources. Record file and line evidence
for each candidate. Do not write anything yet and do not ask questions yet, other than the scope.

### 3. Reconcile

Look up what the catalog already holds with `search_catalog` (by kind and name first, similar names second) and
`get_entity` for matches. Give each candidate a status:

| Status        | Meaning                                                                                 |
|---------------|-----------------------------------------------------------------------------------------|
| `new`         | not in the catalog                                                                      |
| `update`      | in the catalog, and the code differs                                                    |
| `unchanged`   | in the catalog and matches                                                              |
| `investigate` | in the catalog (in the surveyed system) with no counterpart in the code; left untouched |

Do this before the interview so you do not ask about things the catalog already settles.

### 4. Interview

Ask the structural questions that remain, one at a time, using the question bank and recommended-answer
templates in [references/interview.md](references/interview.md). Stop asking when the structure is settled.
Ask which language to use for titles and descriptions once (shared rules), and which existing group owns each
system.

### 5. Plan

Present the plan in the conversation in the format of [references/plan-format.md](references/plan-format.md): every
entity and relationship with its status and evidence, the open uncertainties, and the `investigate` list. If the
user wants changes, revise and show it again; write nothing. Write a plan file only if the user asks for one.

### 6. Handoff

Only after the user approves the plan, hand it to `atlas-curator` using the handoff text in
[references/plan-format.md](references/plan-format.md). From there the curator owns the summary, the confirmation,
and the writes. Do not create any entity yourself. If the user declines the plan, revise it or stop.

## References

- [references/discovery.md](references/discovery.md): what to look for in the code
- [references/interview.md](references/interview.md): questions, recommendations, and what not to ask
- [references/plan-format.md](references/plan-format.md): plan layout and handoff to the curator
- [../atlas-curator/references/entities.md](../atlas-curator/references/entities.md): entity kinds and types
- [../atlas-curator/references/conventions.md](../atlas-curator/references/conventions.md): names and refs
- [../atlas-curator/references/shared-rules.md](../atlas-curator/references/shared-rules.md): rules shared by all Atlas
  skills

## Shared rules

Read `../atlas-curator/references/shared-rules.md` before the first catalog read or write.
If that file is not available, stop and tell the user to install the full set of Atlas
skills. In short:

1. **Preflight.** Check which Atlas MCP tools exist; stop if none, name what is missing,
   continue at reduced capability only if the user agrees. Report permission errors; do not retry.
2. **Language.** Follow the user's language; ask once which language to use for titles and
   descriptions; keep `name` identifiers, field names, and enum values in English.
3. **Confirm.** Show a summary of what will change and write nothing until the user confirms.
4. **No removal.** Never remove, purge, or delete entities or flows; removal is done in the Atlas web UI.
