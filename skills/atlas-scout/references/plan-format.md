# Plan format and handoff

## Plan shown in the conversation

Show the plan in the user's language (field names, enum values, and `name` identifiers stay in English). Use this
shape:

```
Plan: <scope surveyed>   (language for titles and descriptions: <language>)

Systems
- [new]       system:payments  "Payments"  owner: group:platform-team
                evidence: README.md:1

Components
- [new]       component:billing-service  service / production  system: payments
                provides: api:billing-api   depends on: resource:billing-db
                evidence: services/billing/Dockerfile:12
- [update]    component:web  website / production -- differs from the catalog: lifecycle experimental -> production
                evidence: web/package.json:5
- [unchanged] component:ledger-worker

Resources
- [new]       resource:billing-db  database  system: payments
                evidence: docker-compose.yml:20

APIs
- [new]       api:billing-api  openapi  spec: services/billing/openapi.yaml (attach inline)
                evidence: services/billing/openapi.yaml:1

Relationships
- [new]       component:web -> component:billing-service  "Makes API calls to"  REST/HTTPS  synchronous
                evidence: web/src/config.ts:8

Needs a decision
- component:notifier: service or worker? evidence is mixed (notifier/app.py:3, notifier/tasks.py:10)

Investigate (in the catalog, not found in the code; left untouched)
- component:legacy-export
```

Rules:

- One line per entity or relationship with its status (`new`, `update`, `unchanged`, `investigate`), its key
  fields, and at least one `path:line` of evidence. `update` says what differs.
- Uncertain items go under "Needs a decision" and are not handed over until the user decides.
- `investigate` items are listed only to be looked at; they are never proposed for removal.
- Titles and descriptions are drafted but may be abbreviated in the plan; offer to show them in full.
- End with: "Approve this plan, or tell me what to change." Do not hand over before an explicit approval.

## Handoff to atlas-curator

After approval, continue as `atlas-curator` (read its SKILL.md and follow its workflow) with this text, filled in:

```
Approved plan from atlas-scout. Apply it with the curator workflow.
- Content language for titles and descriptions: <language>
- Owner choices: <system> -> <group ref>, ...
- Items: <the plan's entities and relationships with their statuses, in full: kind, name, title,
  description, spec fields, tags, API spec file paths and how to attach them>
- Skip: items marked investigate or unchanged; items under "Needs a decision" that were not resolved.
The curator shows its own change summary (from dry-run when available) and waits for confirmation before writing.
```

The scout does not write, summarize writes, or report results after handoff; the curator's ledger is the
report. If the user approved the plan, that is approval of the plan only: the curator still asks for confirmation
of the change summary.
