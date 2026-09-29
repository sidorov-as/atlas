## Why

A prerelease security audit found that production Django settings silently fall back to unsafe or non-functional defaults instead of refusing to start: `DJANGO_SECRET_KEY` defaults to the literal string `"unsafe-development-secret"`, Compose defaults `POSTGRES_PASSWORD` to `atlas` and `DJANGO_SECURE_SSL_REDIRECT` to `false`, and the mail backend is hardcoded to `locmem.EmailBackend` everywhere — meaning any deployment that forgets to override one of these fails silently rather than loudly, and password-recovery emails silently vanish instead of being sent or being refused. `python manage.py check --deploy` currently fails because of this. A public open-source project should not ship defaults that turn a missed environment variable into a security hole or a silently broken feature.

## What Changes

- `DJANGO_SECRET_KEY` in production SHALL be required to be explicitly set to a non-default, sufficiently random value; startup SHALL fail (not silently substitute a fallback) when it is missing, equal to a known example/placeholder value, or below a minimum entropy/length threshold. The `"unsafe-development-secret"` fallback SHALL only be reachable from development settings, never from a production settings path.
- `docker-compose.yml`'s production-facing service definitions SHALL require `POSTGRES_PASSWORD` to be explicitly supplied rather than defaulting to `atlas`, and SHALL require `DJANGO_SECURE_SSL_REDIRECT` to default to `true` (or be explicitly required) in that context, rather than `false`.
- The application SHALL require an explicit, real mail backend to be configured before password-recovery is reachable in a production-like environment; if none is configured, password-recovery SHALL be disabled rather than silently discarding emails via `locmem`.
- `python manage.py check --deploy` SHALL pass once these changes land (the mail-backend and secret-key/SSL-redirect warnings it currently raises SHALL be resolved).
- Development defaults (the current `unsafe-development-secret`, `atlas` password, `locmem` mailer) remain available for local development — nothing here removes local dev convenience, it only prevents those defaults from being reachable in production.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `backend-platform-foundation`: The "Baseline operational and security configuration" requirement currently describes health reporting, logging, production serving, security middleware, and SPA session/CSRF configuration, but says nothing about secrets or mail configuration failing closed. This change extends it: production configuration for `SECRET_KEY`, database credentials, HTTPS redirect, and mail delivery SHALL fail closed (refuse to start, or refuse to offer the dependent feature) rather than silently falling back to development-safe defaults.

## Impact

- `core/backend/server/settings/components/common.py`: `SECRET_KEY` default (line ~19) and `MAILERS` default backend (line ~310) move behind an explicit production-vs-development branch instead of being unconditional.
- `core/backend/server/settings/environments/production.py`: gains the actual fail-closed enforcement (this file already sets `SECURE_SSL_REDIRECT` default `True` at the Django-settings level — the audit's "HTTPS redirect off by default" concern is specifically about the Compose-level `DJANGO_SECURE_SSL_REDIRECT` environment variable default of `false`, verified in `docker-compose.yml` line ~34).
- `docker-compose.yml`: `POSTGRES_PASSWORD` (line ~7) and `DJANGO_SECURE_SSL_REDIRECT` (line ~34) defaults change for any production-facing service definition.
- No API, schema, or migration changes. No impact on development workflow defaults.
- Independent of the other prerelease-hardening changes (`fix-ingestion-path-traversal`, `add-safe-http-helper`, `fix-apis-ssrf`, `fix-auth-dns-rebinding`, `harden-input-field-limits`) — no shared files, can land in any order relative to them. Should land after `ruff-cleanup` per that change's sequencing note, since it touches Python settings files.
