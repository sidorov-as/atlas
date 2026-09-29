## 1. Plugin-API secret resolution (foundation, no behavior change for existing plugins)

- [x] 1.1 Add `FileRef` (`from_file: str`, alias `fromFile`) as a sibling type to `SecretRef` in `plugin-api/python/atlas_plugin_api/config.py`
- [x] 1.2 Update `_is_secret_capable` and `PluginConfigSchema.redacted_dump`/`public_projection`/`has_unresolved_secrets` to also recognize `FileRef`
- [x] 1.3 Extend `resolve_secrets` to recurse into `BaseModel` and `list[BaseModel]`-typed fields, resolving `SecretRef`/`FileRef` wherever found, rebuilding each nested model via `model_validate`
- [x] 1.4 Implement `FileRef` resolution: read file contents at the given path; raise a clear, field-naming error (mirroring `MissingSecretEnvError`) if the path is missing or unreadable
- [x] 1.5 Unit tests: top-level `fromEnv` (existing, must still pass), top-level `fromFile`, a `SecretRef`/`FileRef` nested inside a list of sub-models, a missing env var, a missing/unreadable file, and confirm redaction still hides both reference kinds in `repr`/`redacted_dump`

## 2. `GitConnector` implementation

- [x] 2.1 Add `dulwich` and `paramiko` to `core/backend/pyproject.toml`; spike shallow-clone (`depth=1`, single-branch) and SSH-vendor behavior against a local Gitea instance before pinning exact versions
- [x] 2.2 Implement `GitConnector` against the existing `SourceConnector` ABC (`connectors/base.py`): clone to a per-call temporary directory, `os.walk` for `**/catalog-info.yaml`, read files from the checkout, resolve `HEAD` sha
- [x] 2.3 HTTPS auth: support `authKind: basic` and `authKind: bearer` by supplying credentials via request headers (never embedded in the clone URL)
- [x] 2.4 SSH auth: wire dulwich's SSH vendor to `paramiko`; support `authKind: ssh-key` using a `FileRef`-resolved private key
- [x] 2.5 SSH host-key verification: require known-hosts content/path, or an explicit development-only `acceptUnknownHostKeys` opt-in; fail closed (raise, don't prompt or silently trust) when neither is configured
- [x] 2.6 Enforce transport scheme allowlist (`https://`, `http://`, `ssh://` only) at the connector boundary
- [x] 2.7 Add a wall-clock timeout per clone operation; ensure the temporary directory is removed in a `finally` block on every code path
- [x] 2.8 Unit/integration tests: successful HTTPS clone and SSH clone against a throwaway local git server, nested manifest discovery, timeout behavior, cleanup-on-failure, and a test asserting no `subprocess` call occurs during either transport

## 3. `sources` plugin config and `RegisteredRepository` schema

- [x] 3.1 Define the `atlas.ingestion` plugin config schema addition: `sources: list[SourceConfig]`, each with `id`, `baseUrl`, `authKind` (`basic` | `bearer` | `ssh-key`), `credential: str | SecretRef | FileRef`, and SSH-specific host-key fields for `authKind: ssh-key`
- [x] 3.2 Decide and implement `baseUrl` outbound-trust validation (`allowedDestinations`/`allowDevelopmentHttp`-style, matching `plugins/auth-gitea/backend/atlas_plugin_auth_gitea/config.py`'s pattern) — resolve the corresponding Open Question in `design.md` before or during this task
- [x] 3.3 Write the `RegisteredRepository` migration: drop `full_name` and `access_token`, add `source_id` and `path`, keep `default_branch`
- [x] 3.4 Add `path` validation (reject empty, leading `/`, `..` segments, control/whitespace characters, `://`) at the model/admin-form level
- [x] 3.5 Add `source_id` validation against the currently resolved `sources` config at admin-form `clean()` time; decide free-text-with-validation vs. dynamically populated `ChoiceField` per the corresponding Open Question in `design.md`
- [x] 3.6 Update `admin.py`: `RegisteredRepositoryAdmin.list_display`/`search_fields` for the new fields
- [x] 3.7 Update `pipeline.py`/`plugin.py`: resolve `GitConnector` per repository's configured source (via `source_id`) instead of importing a hardcoded `CONNECTOR_ID`; surface a clear error (not a silent skip) when a repository's `source_id` no longer matches any configured source

## 4. Remove the GitHub-specific connector

- [x] 4.1 Delete `connectors/github.py` and its dedicated tests
- [x] 4.2 Update any remaining references to `GitHubConnector`/`GITHUB_API_BASE` across `plugins/ingestion/backend/` (grep for both before considering this done)
- [x] 4.3 Update existing ingestion tests that construct `RegisteredRepository(full_name=..., access_token=...)` (e.g. `tests/conftest.py`, `tests/test_arbitration.py`, `tests/test_ingestion.py`) to the new `source_id`/`path` shape

## 5. Documentation

- [x] 5.1 Rewrite `docs-site/docs/using-atlas/ingest-repository.md`'s registration steps for the `source_id`/`path` model and the manifest-level `sources` config
- [x] 5.2 Update `docs-site/docs/using-atlas/troubleshoot-ingestion.md` for the new failure modes (unresolved `source_id`, invalid `path`, SSH host-key misconfiguration)
- [x] 5.3 Update any `RegisteredRepository`/credential references in `docs-site/docs/concepts/catalog-info-yaml.md` or elsewhere that describe the old `owner/repo` + access-token flow

## 6. `examples/ingestion/`

- [x] 6.1 Scaffold `examples/ingestion/` following `examples/authentication/oauth2-gitea/`'s structure: `compose.yaml`, `.env.example`, `gitea/` (app.ini, start.sh, bootstrap scripts), README, smoke script
- [x] 6.2 Select and write the curated `catalog-info.yaml` fixture set (proposed: `search-discovery`, `booking-reservations`, `payments-payouts` Systems with their Components/Resources/APIs and `dependsOn`/`consumesApis`/`relationships`, one repository per System) derived from `seed_booking_demo.py`
- [x] 6.3 Add a one-shot bootstrap container/script that creates the fixture repositories in Gitea via its API and pushes the `catalog-info.yaml` content into each
- [x] 6.4 Add an ORM bootstrap step (`manage.py shell < bootstrap.py`, following the existing `oauth2-gitea/bootstrap.py` pattern) that pre-creates every owner Group the fixture manifests reference, since `catalog-info.yaml` cannot declare `kind: Group`
- [x] 6.5 Configure the example's manifest with a `gitea-primary` source (`sources[]` in `atlas.ingestion` config) and register the fixture repositories as `RegisteredRepository` rows against it
- [x] 6.6 Add a one-shot compose service that runs `manage.py ingest` once at startup so entities are visible immediately after `docker compose up`
- [x] 6.7 Wire up `atlas.auth.gitea` for login, reusing `examples/authentication/oauth2-gitea`'s OAuth-app bootstrap approach
- [x] 6.8 Add the `seed_admin` bootstrap step so Django `/admin/` is actually reachable (existing `oauth2-gitea` example omits this despite referencing Django admin in its README — do not repeat that gap)
- [x] 6.9 Write `examples/ingestion/README.md`: audience, architecture, prerequisites, startup/cleanup commands, signing in to Gitea, signing in to Atlas (Gitea OAuth and Django `/admin/`, with the `seed_admin` step spelled out), the owner-Group pre-creation step, editing a `catalog-info.yaml` in the Gitea web UI, re-running ingestion (`manage.py ingest`; note there is currently no Django-admin action to trigger a run), and verifying the resulting entity
- [x] 6.10 Add/adapt a smoke script exercising the full round trip: stack up → entities present → edit a manifest via the Gitea API → re-run ingestion → assert the change landed
- [x] 6.11 Verify `docker compose config` renders successfully with documented placeholder values only (no untracked secret file required), matching the existing authentication examples' CI expectation — `docker compose config --quiet` passes. Also ran `core/backend/poetry.lock` regeneration (it was stale relative to `pyproject.toml`'s `dulwich`/`paramiko`/auth-plugin additions, blocking every example's backend build; fixed out of band, see below) and then a full `docker compose build` + `docker compose up`: the stack comes up clean on a fresh volume set, `ingest-once`'s two-pass `manage.py ingest` resolves the cross-repo `consumesApis` reference, and `smoke.sh` passes end to end. Fixed two real bugs found during this verification: `compose.yaml`'s `x-backend-environment` anchor was missing `GITEA_INSTANCE_ORIGIN`/`GITEA_ALLOWED_DESTINATIONS`/`GITEA_ALLOW_DEVELOPMENT_HTTP` (present in the `oauth2-gitea` template but dropped here), and `smoke.py`'s `django_shell`/re-ingest `compose exec` calls didn't source `/run/atlas-ingestion/{gitea,ingestion}.env` before invoking `manage.py`, unlike `oauth2-gitea/browser_smoke.py`'s equivalent.

## 7. Verification

- [x] 7.1 Run the full `plugins/ingestion` test suite plus the new connector/plugin-api tests
- [x] 7.2 Run `examples/ingestion/smoke.sh` (or equivalent) end to end locally
- [x] 7.3 Confirm `openspec validate --change add-universal-git-ingestion-connector` passes before archiving
