## Context

`docker-compose.dev.yml` defines a `migrate` service (`python manage.py migrate --noinput`), and both `backend` and the ingestor declare `depends_on: migrate: condition: service_completed_successfully`. Migrations therefore already run automatically, once, before `backend` becomes reachable, as part of a single `docker compose ... up --build`. The root README's "Get started" section was written before this automation existed (or wasn't updated after it landed) and still tells the reader to run migrations manually in a second terminal after the stack is up.

## Goals / Non-Goals

**Goals:**
- README accurately describes what `up --build` already does, with no redundant manual step presented as required.
- No change to actual Compose or migration behavior — this is a documentation-only fix.

**Non-Goals:**
- Changing how migrations run (the `migrate` service, its dependency wiring, or production Compose behavior) — out of scope, this change only corrects documentation to match existing behavior.
- Auditing the rest of the README beyond this specific drift — a broader README pass is not part of this change.

## Decisions

- **Remove the manual migration step from the primary path rather than just annotating it as "already automatic."** Keeping an instruction that's simultaneously described as unnecessary invites confusion about whether it's actually needed. If a manual/diagnostic migration command is worth keeping (e.g. for the "Operational recovery instructions" requirement in `developer-launch-documentation`, which already covers migrations/logs/recovery), it belongs there, explicitly framed as optional, not in "Get started".

## Risks / Trade-offs

- **None of substance** — this is a low-risk documentation correction with no code or runtime impact. The only risk is under-scoping (missing a related stale instruction nearby) or over-scoping (rewriting more of the README than the drift warrants); this change stays strictly to the migration-instruction discrepancy.

## Migration Plan

1. Update the README's "Get started" section to remove or correct the manual migration instruction.
2. If useful, add a brief, clearly-optional note about manually re-running `manage.py migrate` for diagnostic purposes, likely alongside the README's existing operational-recovery content.
3. No rollback complexity — plain text change.

## Open Questions

- None.
