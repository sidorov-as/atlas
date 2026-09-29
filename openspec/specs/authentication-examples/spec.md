# authentication-examples Specification

## Purpose
Provide isolated, runnable, and continuously validated authentication examples that demonstrate supported provider flows and complete operator journeys.

## Requirements

### Requirement: Authentication examples are isolated runnable Compose projects
The repository SHALL contain `examples/authentication/` with a discoverable index and separate runnable directories for `local`, `oidc-keycloak`, `oauth2-gitea`, and `custom-credentials`. Each example SHALL declare its own Compose file, `.env.example`, provider fixtures/configuration, and README while reusing repository build inputs without depending on another example's running services.

#### Scenario: Reader selects an example
- **WHEN** a reader opens `examples/authentication/README.md`
- **THEN** they see a comparison of supported flows, intended use, production caveats, provisioning/group behavior, resource requirements, and links to each isolated example

#### Scenario: Compose configuration is rendered
- **WHEN** CI runs `docker compose config` for any authentication example with documented placeholder values
- **THEN** the project resolves successfully without requiring an untracked secret file

### Requirement: Every example documents a complete operator journey
Each authentication example README SHALL state audience, architecture, prerequisites, exact startup and cleanup commands, URLs, disposable credentials or credential-generation steps, callback/origin configuration, secrets, selected/default providers, user and Actor provisioning, Group mapping, permissions verification, logout semantics, troubleshooting, and explicit production limitations.

#### Scenario: Reader completes an example
- **WHEN** a reader follows an example README on a supported development machine
- **THEN** they can start the topology, authenticate, verify one permitted and one denied catalog action, inspect the resulting Principal/Actor/Group state, log out, and clean up

#### Scenario: Example contains disposable credentials
- **WHEN** an example ships a fixed test password or client secret
- **THEN** the README and configuration identify it as disposable development-only data and do not present it as a production default

### Requirement: The local example demonstrates closed signup and controlled bootstrap
The local example SHALL run Atlas with only `atlas.auth.local`, self-signup disabled, and a documented controlled bootstrap mechanism for the first administrator. It SHALL demonstrate the distinction between a Principal, linked Actor, Group membership, and superuser status.

#### Scenario: Anonymous user calls signup
- **WHEN** an anonymous caller invokes the local signup endpoint in the local example
- **THEN** registration is rejected even though local login remains available

#### Scenario: Bootstrap account signs in
- **WHEN** the operator creates the disposable administrator through the documented bootstrap command or injected secret
- **THEN** that account can authenticate without the example storing a production password in version control

### Requirement: The Keycloak example demonstrates standards-based OIDC
The OIDC example SHALL run Atlas, PostgreSQL, and Keycloak with an importable development realm containing an Atlas client, safe development callback/origin values, test users, and test groups. Atlas SHALL run OIDC-only by default while the README explains how to add an explicit local fallback.

#### Scenario: Keycloak user authenticates
- **WHEN** a supplied test user signs in through Keycloak
- **THEN** Atlas validates the OIDC flow, provisions according to the example policy, maps the configured groups claim, and establishes a normal Atlas session

#### Scenario: Keycloak membership is removed
- **WHEN** the example uses exact reconciliation and a test user's Keycloak group is removed before the next login
- **THEN** the next successful login removes only the corresponding Keycloak-managed Atlas membership

### Requirement: The Gitea example demonstrates provider-specific OAuth2
The OAuth2 example SHALL run Atlas, PostgreSQL, and Gitea with repeatable development bootstrap for an OAuth application and test user. The example SHALL describe which provider-specific profile endpoint and stable identifier are used and SHALL NOT describe OAuth 2.0 itself as an identity or group standard.

#### Scenario: Gitea user authenticates
- **WHEN** the test user authorizes Atlas through Gitea
- **THEN** the Gitea adapter resolves a stable external identity, Core provisions it, and Atlas establishes its normal session

#### Scenario: Gitea provides no configured team mapping
- **WHEN** the example provider does not expose supported team/group data
- **THEN** the README and runtime behavior leave Atlas memberships operator-managed rather than inventing authorization from OAuth scopes

### Requirement: A minimal custom credential example proves third-party extensibility
The custom credential example SHALL include a separately packaged backend plugin implemented only against public `atlas_plugin_api` contracts, using deterministic disposable test identities. It SHALL demonstrate non-empty credential verification, stable source/subject, profile assurance, explicit complete/unavailable group snapshots, provisioning, failure sanitization, fallback, packaging, and shared contract tests. The runnable `custom-credentials` topology SHALL require only Atlas and its database; production LDAP integration and an OpenLDAP deployment SHALL NOT be release prerequisites. Fixture credentials SHALL work only under explicit development configuration and the plugin SHALL not be represented as a production identity service.

#### Scenario: Custom plugin passes import-boundary checks
- **WHEN** CI analyzes the example plugin
- **THEN** it contains no imports from Core implementation modules or undocumented allauth internals

#### Scenario: Credentials are invalid or empty
- **WHEN** a caller submits invalid or empty fixture credentials
- **THEN** login fails without persisting the password, creating a session, or revealing whether a username exists

#### Scenario: Provider failure is simulated
- **WHEN** the example simulates unavailable verification or unavailable groups
- **THEN** it exercises the corresponding fail-closed contract behavior and a healthy selected fallback remains usable

### Requirement: LDAP implementability is documented independently of the example
The SDK guide SHALL map a single-step LDAP search-and-bind flow onto the published credential contract: private typed directory config and secrets, bounded verification, stable directory source/UUID, profile assurance, group completeness, and safe failure categories. It SHALL specify TLS certificate/hostname verification, no plaintext downgrade, filter/DN escaping, rejection of empty-password/anonymous/ambiguous binds, and complete pagination before exact reconciliation. Protocol-specific checks SHALL be provider responsibilities while session, eligibility, provisioning, and grant semantics remain Core responsibilities. This guide SHALL not claim that a production LDAP provider ships in this change. A future LDAP implementation SHALL require no change to the v1 credential contract for this flow.

#### Scenario: Author maps LDAP to SDK types
- **WHEN** an author follows the documented LDAP flow using a maintained client library
- **THEN** every required input, verified result, incomplete-group condition, and failure has a documented public contract representation without requiring Core imports

### Requirement: Authentication examples remain validated in CI
CI SHALL validate example file syntax, Compose rendering, provider fixture parsing, secret-leak rules, documentation links, and focused smoke tests. At least one automated browser or HTTP flow SHALL exercise each built-in example topology on its supported CI tier; expensive image-backed tests MAY run in a dedicated integration job but SHALL remain required before release.

#### Scenario: Example configuration drifts
- **WHEN** an example references a removed environment field, invalid callback, missing fixture, or unsupported provider id
- **THEN** CI fails before the example is published

#### Scenario: Secret scanner inspects examples
- **WHEN** CI scans the example tree
- **THEN** only explicitly allowlisted disposable fixtures are accepted and no real deployment secret is present

### Requirement: Examples are self-validating and safely deletable
No requirement, build step, or required check outside `examples/authentication/` and that example's own dedicated CI workflows SHALL depend on the content of a specific authentication example. Each example SHALL validate its own compatibility with the public SDK contract, composer's manifest/lock schemas, and its own documentation through checks that live under `examples/authentication/` and run in that example's own CI workflow(s), triggered both by changes to the example itself and by changes to the upstream surfaces it depends on (the plugin SDK, composer, first-party auth plugins, the docs site).

#### Scenario: An example directory is deleted
- **WHEN** `examples/authentication/custom-credentials` is removed from the repository
- **THEN** the backend's dependency install, both backend Docker images, and the repo-root pytest suite all still succeed; docs-site's fixture-specific accuracy checks (ported to `validate.py`) no longer run there. Cross-reference links in `docs/` and the example's own `README.md` are expected to need updating as part of that deletion, same as any other doc removal — not a build/dependency coupling this requirement covers.

#### Scenario: An upstream contract changes
- **WHEN** the public `atlas_plugin_api` credential-provider contract, a composer schema, or a first-party auth plugin changes in a way the custom credential example no longer matches
- **THEN** the example's own CI workflow fails, independent of whether any file under `examples/authentication/` itself changed
