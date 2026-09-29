## Why

The root README's "Get started" section still instructs developers to run `docker compose ... exec backend python manage.py migrate` manually after `up --build` (README.md, "Keep it running. In another terminal, apply the database migrations"). This is no longer accurate: `docker-compose.dev.yml` already defines a `migrate` service (`command: ["python", "manage.py", "migrate", "--noinput"]`) that `backend` and the ingestor `depends_on` with `condition: service_completed_successfully`, so migrations already run automatically as part of `up --build`, before `backend` starts. A prerelease audit flagged this as README/Compose drift. Documenting a manual step for something Compose already automates undermines "exact commands" trust for a first-time contributor and adds an unnecessary step.

## What Changes

- Remove or correct the README's manual-migration instruction so it accurately reflects that `docker compose ... up --build` already runs migrations automatically via the `migrate` service.
- If a manual migration command is still useful to document for other purposes (e.g. re-running migrations without a full restart, or diagnosing a stuck `migrate` service), keep it but relabel it clearly as optional/diagnostic rather than a required step in the primary "Get started" path.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `developer-launch-documentation`: The "Authoritative full-stack launch guide" requirement already commits the root README to documenting "exact commands" for the dev Compose topology. This change tightens that requirement so documented commands must match what Compose actually automates — a redundant manual step for already-automatic behavior is itself a violation, not just an omission.

## Impact

- `README.md` only (documentation change, no code or Compose behavior change).
- Fully independent of every other change in the current prerelease-hardening batch — zero code overlap, no sequencing dependency.
