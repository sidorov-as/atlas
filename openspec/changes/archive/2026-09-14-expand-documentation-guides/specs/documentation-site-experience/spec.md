## ADDED Requirements

### Requirement: Audience-oriented documentation navigation
The documentation site SHALL organize its primary navigation around reader
intent with landing pages for Overview, Getting Started, Using Atlas,
Operating Atlas, Features and Integrations, Concepts and Architecture, Plugin
Development, Reference, and Project documentation. Each landing page SHALL
identify its intended audience and provide an ordered path through the section.

#### Scenario: Reader selects a journey from the documentation home page
- **WHEN** a reader opens the documentation home page
- **THEN** they can choose a catalog-user, operator, or plugin-author journey and reach the corresponding first task without knowing Atlas's repository structure

#### Scenario: Reader enters a section directly
- **WHEN** a reader opens any top-level section landing page
- **THEN** the page explains who the section is for, what questions it answers, and which page to read first

### Requirement: First useful catalog journey
Getting Started SHALL take a reader from a fresh supported checkout to a
running Atlas instance and then through a visible, useful catalog outcome. It
SHALL cover environment setup, startup, migrations, login, demo data, catalog
navigation, opening an entity and its relationships, health verification, and
role-specific next steps.

#### Scenario: New reader completes the quickstart
- **WHEN** a reader follows Getting Started on a machine that satisfies the documented prerequisites
- **THEN** they can open Atlas, verify backend health, inspect a demo entity and its relationships, and select the next guide for their role

#### Scenario: Quickstart step fails
- **WHEN** a documented startup, migration, login, or demo-data step does not produce its expected result
- **THEN** the guide points to a symptom-specific diagnostic or troubleshooting procedure

### Requirement: Task-oriented catalog user guide
Using Atlas SHALL document the supported everyday catalog workflows, including
browsing, searching, filtering, inspecting entity details, ownership and
relationships, creating and editing manual entities, distinguishing manual
from YAML-managed entities, repository registration and ingestion, and the
Remove, Revive, and Purge lifecycle. Feature-specific workflows for API
definitions and dependencies, C4 diagrams, database schemas, and flows SHALL be
linked from the relevant catalog tasks.

#### Scenario: Catalog user needs to perform an entity action
- **WHEN** a catalog user needs to create, edit, inspect, remove, revive, or purge a supported entity
- **THEN** they can find a guide that states prerequisites and permissions, gives UI or API steps, explains the resulting lifecycle state, and provides a verification step

#### Scenario: YAML-managed entity cannot be edited
- **WHEN** a reader encounters a read-only YAML-managed entity
- **THEN** the user guide explains why the UI blocks the change and directs the reader to the source repository and ingestion workflow

#### Scenario: Repository ingestion is rejected
- **WHEN** a registered repository or entity claim fails ingestion
- **THEN** the documentation explains where to inspect status, how to identify validation or claim conflicts, and which safe corrective actions are available

### Requirement: Supported operator journeys
Operating Atlas SHALL document the supported deployment topology, production
preflight, configuration and secret handling, local and OIDC authentication,
identity and group mapping, distribution composition, migrations, health and
logs, backups and restoration, upgrades, shutdown and recovery, and
symptom-oriented troubleshooting. It SHALL distinguish current support from
future or experimental deployment targets and SHALL NOT present an unsupported
topology as production-ready.

#### Scenario: Operator prepares a production-like installation
- **WHEN** an operator follows the production guide
- **THEN** they receive a checklist covering required secrets, host and origin settings, database state, distribution composition, migrations, startup ordering, and health verification

#### Scenario: Operator upgrades Atlas
- **WHEN** an operator follows the upgrade guide between supported versions
- **THEN** they can identify behavior changes, back up required data, apply migrations in the documented order, verify the result, and find the documented recovery or rollback boundary

#### Scenario: Operator diagnoses authentication failure
- **WHEN** local or OIDC sign-in fails
- **THEN** troubleshooting is organized by observable symptom and covers provider configuration, allowed origins, identity resolution, group claims, and relevant logs without exposing secrets

### Requirement: Distribution assembly guide
The documentation SHALL provide an end-to-end distribution workflow covering
manifest authoring, plugin selection, version and compatibility constraints,
plugin configuration and secret references, lock generation, composition
validation, image build, plugin disablement or removal, data preservation, and
explicit purge. Validation failures SHALL be documented in terms of the action
an operator can take.

#### Scenario: Operator adds a plugin to a distribution
- **WHEN** an operator selects a plugin and follows the distribution guide
- **THEN** they can update the manifest and configuration, generate or verify the lock, run composition preflight, build the distribution, and confirm that the plugin is active

#### Scenario: Composition preflight rejects a distribution
- **WHEN** composition reports an identity, compatibility, dependency, capability, route, configuration, or package-boundary error
- **THEN** the guide maps the failure category to the manifest or plugin contract that must be corrected

#### Scenario: Operator removes plugin functionality
- **WHEN** an operator disables, removes, reinstalls, or purges a plugin
- **THEN** the guide distinguishes contribution suppression, code removal, preserved data, restored functionality, and irreversible data deletion

### Requirement: Complete and consistent feature guides
Every plugin selected by the checked-in default distribution manifest SHALL
have one discoverable feature guide. Each feature guide SHALL identify its
plugin id, purpose, dependencies, enablement, configuration, permissions,
primary user workflows, API surface, operational behavior, extension surface,
limitations, compatibility, and troubleshooting, using explicit "not
applicable" statements where a category does not apply.

#### Scenario: Default distribution gains a plugin
- **WHEN** a plugin id is present in the default distribution manifest
- **THEN** documentation validation confirms that a feature guide with the same plugin id exists and is included in site navigation

#### Scenario: Reader opens the Flows feature guide
- **WHEN** a reader follows the feature navigation for `atlas.flows`
- **THEN** they can learn how to create, query, edit, and inspect supported flows as well as the plugin's configuration, permissions, dependencies, and limitations

### Requirement: End-to-end plugin author journey
Plugin Development SHALL include a decision guide for choosing among Entity
Kinds, Facets, frontend Contributions, Capabilities, Extension Points, and
scheduled jobs, followed by a from-scratch tutorial that produces a runnable
plugin and adds it to a distribution. It SHALL also cover backend-only,
frontend-only, and full-stack shapes; configuration and secrets; permissions;
models and migrations; cross-plugin collaboration; error handling; testing;
debugging; compatibility; versioning; and publishing.

#### Scenario: Author chooses an extension mechanism
- **WHEN** a plugin author describes the behavior or data they want to add
- **THEN** the decision guide identifies the appropriate contract and links to a focused guide and reference for it

#### Scenario: Author completes the first-plugin tutorial
- **WHEN** an author follows the tutorial from an empty plugin package
- **THEN** they create the required backend and frontend declarations, select the plugin in a distribution, pass composition validation and tests, and observe the contribution in a running Atlas instance

#### Scenario: Author tests a plugin
- **WHEN** a plugin author needs confidence before distribution composition
- **THEN** the testing guide distinguishes backend unit and API tests, frontend tests, composition preflight tests, migration safety, and compatibility checks with runnable commands

### Requirement: Layered reference documentation
Reference documentation SHALL cover the catalog manifest format, environment
and plugin configuration, distribution manifest and lock, plugin contracts,
registered kinds and extension identifiers, permissions, management commands,
and HTTP APIs. Generated API documentation SHALL remain the source of truth for
endpoint signatures, while authored guides SHALL explain authentication,
pagination and filtering, errors, common request examples, and how to reach the
generated reference.

#### Scenario: API consumer starts from the authored reference
- **WHEN** a reader needs to call an Atlas HTTP API
- **THEN** they can learn the common authentication, request, pagination, filtering, and error conventions before following a link to the generated endpoint schema

#### Scenario: Reader looks up a configuration value
- **WHEN** a reader searches for an environment or plugin configuration field
- **THEN** the reference identifies its owner, type, default or required status, secret handling, applicable topology, and related task guide

### Requirement: Documentation page contracts and validation
Task guides SHALL state audience, prerequisites, intended outcome, ordered
steps, expected or verification result, relevant permissions, common failure
modes, and next steps. Concept and reference pages SHALL link to the tasks that
apply them. UI instructions SHALL include maintained screenshots when visual
state or control location is material. Documentation CI SHALL build the site,
validate internal links and navigation, verify default-distribution feature
coverage, and validate source-backed examples with the repository's applicable
formatters, parsers, or tests.

#### Scenario: Documentation pull request contains a broken internal link
- **WHEN** CI validates a documentation change whose navigation or internal link target does not exist
- **THEN** the documentation check fails with the source page and unresolved target

#### Scenario: Task guide is reviewed
- **WHEN** a new task-oriented page is added
- **THEN** reviewers can verify its audience, prerequisites, outcome, steps, verification, permissions, failure modes, and next-step links against the shared page contract

#### Scenario: Included example drifts from supported syntax
- **WHEN** a source-backed YAML, Python, TypeScript, shell, or configuration example no longer passes its applicable parser, formatter, smoke test, or focused test
- **THEN** documentation validation fails before the stale example is published

### Requirement: Stable documentation entry points
The documentation reorganization SHALL preserve existing page URLs where they
remain meaningful. A moved page SHALL have a redirect or a maintained legacy
entry page pointing to its canonical replacement, and duplicated content SHALL
identify one canonical source.

#### Scenario: Reader follows an existing documentation link
- **WHEN** a previously published Atlas documentation URL is moved by the new navigation
- **THEN** the reader reaches the replacement content without receiving a not-found page

#### Scenario: README and documentation site cover the same workflow
- **WHEN** detailed setup or operations guidance exists on the documentation site
- **THEN** repository READMEs provide a concise entry point and link to the canonical guide rather than maintaining a conflicting second procedure
