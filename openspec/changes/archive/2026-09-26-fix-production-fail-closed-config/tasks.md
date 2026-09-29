## 1. Investigate current settings and Compose structure

- [x] 1.1 Confirm whether `docker-compose.yml` is a single file (with profiles/overrides) or there are separate dev/prod Compose files, to know exactly where the `POSTGRES_PASSWORD`/`DJANGO_SECURE_SSL_REDIRECT` default changes belong.
- [x] 1.2 Confirm the exact `django-allauth` settings controlling password-recovery availability in `common.py`, to identify the cleanest toggle point.
- [x] 1.3 Check for an existing `.env.example` or documented example secret values, to build the placeholder denylist.

## 2. Fail-closed `SECRET_KEY`

- [x] 2.1 In `environments/production.py`, validate `SECRET_KEY`: reject unset, reject known placeholder values (including `"unsafe-development-secret"`), reject below a minimum length.
- [x] 2.2 Raise `django.core.exceptions.ImproperlyConfigured` (or equivalent fail-closed mechanism) with a message naming the specific problem.
- [x] 2.3 Confirm development (`DJANGO_ENV` unset/`development`) is unaffected — no new required env vars locally.

## 3. Fail-closed mail / password-recovery

- [x] 3.1 Detect in `environments/production.py` whether `MAILERS`/email backend still resolves to `locmem`.
- [x] 3.2 Implement the chosen fail-closed behavior (disable password-recovery at settings-load time, or fail startup — per design.md's decision and its documented fallback condition) when no real mailer is configured.
- [x] 3.3 Add a startup-time log warning when production runs without a real mailer, regardless of which fail-closed mechanism is used.
- [x] 3.4 Verify `python manage.py check --deploy` no longer flags the mail backend when a real backend is configured.

## 4. Compose defaults

- [x] 4.1 Remove the `:-atlas` fallback from `POSTGRES_PASSWORD` in the production-facing Compose service definition(s), requiring it to be explicitly set.
- [x] 4.2 Remove or flip the `:-false` fallback for `DJANGO_SECURE_SSL_REDIRECT` in the production-facing Compose service definition(s).
- [x] 4.3 Confirm development Compose workflow(s) keep their existing convenience defaults unaffected.

## 5. Verification

- [x] 5.1 Run `python manage.py check --deploy` with `DJANGO_ENV=production` and no `SECRET_KEY`/mail configured — confirm it now fails clearly (or already did, but now for the right reasons) rather than warning-and-continuing.
- [x] 5.2 Run it again with a correct production configuration — confirm it passes clean.
- [x] 5.3 Confirm local development startup (`DJANGO_ENV` unset) is unaffected — no new required env vars, no new failures.
- [x] 5.4 Attempt `docker compose up` against the production-facing definition with `POSTGRES_PASSWORD`/`DJANGO_SECURE_SSL_REDIRECT` unset — confirm it now fails fast instead of starting with insecure defaults.
