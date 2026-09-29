## 1. Verify current state

- [x] 1.1 Re-confirm `docker-compose.dev.yml`'s `migrate` service and its `depends_on: condition: service_completed_successfully` wiring on `backend` (and the ingestor, if present) are unchanged at implementation time.
- [x] 1.2 Re-read the README's current "Get started" section, since it may have changed further since this proposal was written.

## 2. Update the README

- [x] 2.1 Remove the manual `docker compose ... exec backend python manage.py migrate` instruction from the primary "Get started" path.
- [x] 2.2 If a manual/diagnostic migration command is worth retaining, add it under the README's operational-recovery content, explicitly labeled optional/diagnostic. (Decision: not retained — the README has no operational-recovery section of its own, and the linked "Operate Atlas" docs-site guide already covers migrations/upgrades/data safety, so adding one here would be out of scope per the design's non-goal of a broader README audit.)
- [x] 2.3 Re-read the full "Get started" section end-to-end to confirm the remaining steps still form a coherent, accurate sequence.

## 3. Verification

- [x] 3.1 Follow the updated README's "Get started" steps against a fresh `docker compose ... up --build` to confirm the app comes up and is usable without any additional manual migration step.
