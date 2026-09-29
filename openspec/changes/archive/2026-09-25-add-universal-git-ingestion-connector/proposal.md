## Why

Ingestion only works against real `github.com` today: `GitHubConnector` hardcodes `https://api.github.com` and is the sole registered implementation of the `atlas.ingestion.connectors.v1` extension point, even though that extension point was deliberately designed to be swappable. Any self-hosted git service (Gitea, GitLab, Bitbucket, GitHub Enterprise) is unreachable, and `RegisteredRepository.access_token` is a plaintext database column with no outbound-trust validation on the requests it drives. There is also no example showing ingestion working end to end against a self-hosted git service, unlike authentication, which already has four.

## What Changes

- Replace `GitHubConnector` with a single provider-agnostic `GitConnector` that discovers and reads `catalog-info.yaml` via a shallow (`depth=1`, single-branch) clone over HTTPS or SSH, using `dulwich` (pure-Python git) with a `paramiko`-backed SSH vendor — no `subprocess` git/ssh invocation, closing the `ext::`-transport and SSH-flag-injection command-injection classes by construction. **BREAKING**: `GitHubConnector` and its GitHub-specific request/response handling are removed.
- Move git-host connection details and credentials out of the database entirely. `atlas.ingestion` plugin config gains a `sources` list (id, `baseUrl`, `authKind`: `basic` | `bearer` | `ssh-key`, `credential`), declared in the manifest and resolved once at process startup via the existing `SecretRef`/`resolve_secrets` mechanism — the same pattern `atlas.auth.gitea`/`atlas.auth.oidc` already use for OAuth client secrets.
- `RegisteredRepository` **BREAKING** schema change: replace `full_name` (GitHub-shaped `owner/repo`) and `access_token` (plaintext) with `source_id` (references a configured source) and `path` (repo path relative to that source's `baseUrl`). No ingestion credential is stored in the database after this change. `path` is validated to prevent path-traversal/URL-injection (no `..`, control characters, or scheme-like prefixes).
- Extend `resolve_secrets` (`plugin-api/python/atlas_plugin_api/config.py`) to recurse into nested `BaseModel`/`list[BaseModel]` config fields — required for `sources[].credential`, and reusable by any future plugin with a list of sub-configs containing secrets.
- Add a `{fromFile: <path>}` secret reference alongside the existing `{fromEnv: VAR}` `SecretRef`, for SSH private key material (the project's first multi-line secret), matching the standard mounted-secret-file idiom already used for other runtime secrets in the example topologies.
- Add host-key handling for `authKind: ssh-key` sources (known-hosts content/path, with an explicit development-only unknown-host-acceptance opt-in) so a scheduled ingestion pass never blocks on an interactive prompt and never silently trusts an unverified host.
- Add `examples/ingestion/`: a Gitea-backed runnable example (following `examples/authentication/oauth2-gitea`'s compose/bootstrap structure) that provisions a few repositories with `catalog-info.yaml` manifests derived from a curated subset of the `seed_booking_demo` fixture, pre-creates their owner Groups (which `catalog-info.yaml` cannot declare), registers them as a configured source + `RegisteredRepository` rows, runs one ingestion pass automatically at startup, and reuses `atlas.auth.gitea` for login. Its README documents the full operator journey: start the stack, sign in to Gitea, sign in to Atlas (both via Gitea OAuth and via Django `/admin/`, including the `seed_admin` step existing examples omit), edit a manifest in the Gitea UI, re-run ingestion, and verify the change landed.

## Capabilities

### New Capabilities
- `ingestion-examples`: isolated, runnable, documented example(s) under `examples/ingestion/` demonstrating repository registration and ingestion against a self-hosted git service, mirroring the operator-journey guarantees `authentication-examples` already makes for auth.

### Modified Capabilities
- `catalog-ingestion`: "Registered repository configuration" changes from `{owner/repo, default branch, access token}` to `{source_id, path, default branch}` with no stored credential; "Manifest discovery via the connector interface" changes from "`GitHubConnector` SHALL be the only v1 implementation" to a provider-agnostic `GitConnector` serving any configured source over HTTPS or SSH.
- `ingestion-plugin`: the "Connectors and parsers are plugin-owned extension points" requirement's scenario currently names `GitHubConnector` specifically as the registered implementation; it now names the universal `GitConnector`, registered per configured source rather than hardcoded to one host.
- `plugin-configuration-isolation`: "Secrets are resolved centrally and never exposed" extends to secret references nested inside list/sub-model config fields (not just top-level fields), and to a new `{fromFile: ...}` secret-reference kind alongside `{fromEnv: ...}`.

## Impact

- `plugins/ingestion/backend/atlas_plugin_ingestion/`: `models.py` (new migration replacing `full_name`/`access_token` with `source_id`/`path`), `connectors/github.py` removed, new `connectors/git.py` (or similar), `pipeline.py`, `admin.py`, `extension_points.py`/`plugin.py` registration, new plugin config schema (`sources`).
- `plugin-api/python/atlas_plugin_api/config.py`: `resolve_secrets` recursion, new `fromFile` secret reference kind.
- `core/backend/pyproject.toml`: new dependencies `dulwich`, `paramiko`.
- `examples/ingestion/` (new): compose file, Gitea bootstrap, repository/manifest seeding, README.
- Docs: `docs-site/docs/using-atlas/ingest-repository.md`, `docs-site/docs/concepts/catalog-info-yaml.md` reference to `RegisteredRepository` fields, `docs-site/docs/using-atlas/troubleshoot-ingestion.md` — all describe the old `owner/repo` + access-token registration flow and need updating to the `source`/`path` model.
- No change to `EntityIntent`/`EntityKindHandler`/upsert/validation/claim-arbitration pipeline stages — this change is scoped to discovery/fetch (the connector) and repository configuration, not to how a discovered manifest becomes an entity.
