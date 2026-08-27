# Custom credential provider example

This disposable development topology proves that an independently packaged
credential provider can authenticate through the public
`atlas.auth.providers.v1` SDK without importing Authentication Core, Django
models, session helpers, or allauth internals. It runs only Atlas and
PostgreSQL; there is no directory service and no production LDAP provider.

## Architecture and policy

```text
browser :18080 -> Atlas frontend -> Atlas authentication gateway
                                      |
                         example.auth.fixture plugin
                                      |
                         deterministic in-memory users
                                      |
                         Core provisioning -> PostgreSQL
```

The checked-in [manifest](manifest.yaml) selects the fixture provider first
and `atlas.auth.local` as a healthy fallback. The fixture provider uses
automatic Principal and Actor provisioning, provider-managed profile fields,
and exact group reconciliation. `fixture-platform` maps to the pre-created
Atlas Group `custom-platform`; unknown values cannot grant access.

The plugin is a real package under [plugin/](plugin/) with its own
`pyproject.toml`, entry point, static descriptor, typed config, runtime
registration, implementation, and tests. Its Atlas imports come exclusively
from `atlas_plugin_api`. Core still owns selection, attempts, rate limits,
provisioning, sessions, CSRF, logout, Group grants, and authorization.

## Disposable fixture identities

All valid users share `ATLAS_FIXTURE_PASSWORD` from the example `.env` file.
The value reaches only the typed backend config after its `SecretRef` is
resolved; the lock retains only the environment-variable name, and the value
is absent from the lock and public bootstrap response.

| Username                     | Stable subject                       | Group result                 | Expected Core behavior                                              |
|------------------------------|--------------------------------------|------------------------------|---------------------------------------------------------------------|
| `fixture-alice`              | `fixture-user-alice-v1`              | complete: `fixture-platform` | Provision once and maintain one exact `custom-platform` grant       |
| `fixture-empty`              | `fixture-user-empty-v1`              | complete empty               | Provision, remove this identity's prior exact grants, grant nothing |
| `fixture-groups-unavailable` | `fixture-user-unavailable-groups-v1` | unavailable                  | Fail provisioning closed; do not create a session or renew grants   |
| `fixture-provider-outage`    | none                                 | provider unavailable         | Return a sanitized retryable failure; local fallback remains usable |

Invalid known and unknown usernames return the same `invalid_credentials`
category. Empty passwords are rejected before provider invocation. The plugin
uses constant-time password comparison and never stores credential inputs.
Email has verified-ownership assurance and display name has authority-managed
assurance; neither becomes a permission or administrative flag.

## Prerequisites

- Docker Engine with Docker Compose v2
- Python 3.11+ for the HTTP smoke driver
- about 2 GB free RAM, 2 CPU cores, and 4 GB disk for the first build

## Start and authenticate

From this directory:

```bash
cp .env.example .env
docker compose config --quiet
docker compose up --build -d
docker compose ps
```

Open <http://localhost:18080/login?choose-provider=1>. Use `fixture-alice`
and `ATLAS_FIXTURE_PASSWORD` from `.env`. The credentials are deliberately
fixed, development-only fixtures. Never expose this topology to untrusted
networks or reuse any example password.

The fallback form uses `ATLAS_LOCAL_FALLBACK_USERNAME` and
`ATLAS_LOCAL_FALLBACK_PASSWORD`. Local signup remains closed; selecting local
does not create accounts automatically.

## Verify the complete journey

Run:

```bash
./smoke.sh
```

The smoke test checks valid, invalid, empty, and unknown-account credentials;
account-existence indistinguishability; simulated provider outage with healthy
local fallback; automatic Principal/Actor provisioning; stable repeated login;
complete mapped and complete-empty snapshots; unavailable-group fail-closed
behavior; a finite exact-grant expiry; permitted owner-Group write; denied
unowned write; credential redaction from responses/logs; and logout.

The separately packaged contract suite can also run without repository-private
fixtures:

```bash
uv run --project plugin --with pytest --with pytest-django \
  python -m pytest -q
```

The repository import-boundary test statically restricts this example package
to Python's standard library, Pydantic, its own modules, and
`atlas_plugin_api`.

## SDK lifecycle demonstrated here

1. Composition imports `plugin.py` without Django setup, validates the static
   descriptor and `FixtureCredentialConfig`, and keeps only the unresolved
   `fromEnv` reference in the lock/generated module.
2. Core resolves that reference in memory and publishes only the provider's
   safe presentation metadata to the browser.
3. Runtime activation registers `FixtureCredentialProvider` through
   `register_authentication_provider`.
4. Core creates a bounded `CredentialFlowContext` and ephemeral
   `CredentialInput`; the provider returns `VerifiedIdentity` or an allowlisted
   `AuthenticationFailure`.
5. Core validates source/provider identity, provisions state transactionally,
   reconciles exact grants, and only then creates the ordinary Atlas session.

For a production directory implementation, follow
[LDAP-MAPPING.md](LDAP-MAPPING.md). It maps search-and-bind to every public SDK
input/result and lists the protocol checks the provider must own. Atlas does
not ship or certify a production LDAP provider.

## Troubleshooting

- **Provider unavailable at startup:** confirm `ATLAS_FIXTURE_PASSWORD` is set
  and the generated settings select `atlas_example_auth_fixture.plugin`.
- **Fixture config rejected:** `developmentEnabled` must be explicitly true and
  `sourceId` must use `urn:atlas:directory:fixture-*`. This is an intentional
  guard against presenting fixture identities as production configuration.
- **Login returns `provisioning_failed`:** `fixture-groups-unavailable` is
  expected to fail because exact mode accepts only a complete snapshot. For
  other users, verify the source binding and `custom-platform` bootstrap.
- **Login succeeds but a write is denied:** inspect the Principal-to-Actor link,
  effective grant sources/expiry, owner Group, and independent read-only flag.
  Provider attributes do not directly authorize.
- **Fallback fails:** verify the initializer completed and the two local
  fallback environment variables match the submitted values.

Do not print submitted passwords, complete credential objects, or raw provider
exceptions while troubleshooting. Use sanitized categories and correlation ids.

## Logout and cleanup

`DELETE /auth/browser/v1/session` ends the same local Atlas session for fixture
and local authentication. The fixture provider has no remote session.

```bash
docker compose down --volumes --remove-orphans
```

This removes the isolated PostgreSQL volume and all provisioned example data.

## Production differences

This package is installed only through the backend development dependency
group, is absent from the default distribution selection, requires an explicit
development gate, and verifies in-memory fixture data. A production provider
requires reviewed dependencies and artifact provenance, protected secret
delivery, bounded and monitored network operations, TLS/outbound policy,
directory-specific correctness, operational health, load/failure testing, and
the full contract/security suite. Installed plugins are trusted server code;
the narrow SDK and import checks are collaboration boundaries, not a sandbox.
