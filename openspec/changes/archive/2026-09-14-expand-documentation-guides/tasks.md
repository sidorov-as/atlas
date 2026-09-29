## 1. Content inventory and authoring contracts

- [x] 1.1 Inventory every current documentation URL and classify each page as keep, expand, move, replace, or legacy entry point
- [x] 1.2 Build a capability-to-documentation matrix from the default distribution manifest, current OpenSpec specs, runtime configuration, permissions, management commands, and supported UI workflows
- [x] 1.3 Define the front matter and review checklist for section landing pages, tutorials, task guides, feature guides, concepts, and references
- [x] 1.4 Define the source-backed example layout and the applicable validation command for YAML, Python, TypeScript, shell, and configuration examples
- [x] 1.5 Define a screenshot capture checklist based on the checked-in demo seed, including viewport, theme, data state, filename, alt text, and recapture triggers

## 2. Information architecture and first useful journey

- [x] 2.1 Add landing pages for Overview, Getting Started, Using Atlas, Operating Atlas, Features and Integrations, Concepts and Architecture, Plugin Development, Reference, and Project
- [x] 2.2 Replace the site navigation with the audience-oriented hierarchy while keeping every retained current page reachable
- [x] 2.3 Rewrite the documentation home page to explain Atlas, show its supported product shape, and route catalog users, operators, and plugin authors to their first tasks
- [x] 2.4 Expand Getting Started from environment setup through startup, migrations, login, demo seeding, health verification, catalog inspection, relationships, and role-specific next steps
- [x] 2.5 Add a short visual catalog tour using reproducible demo entities and maintained screenshots for the home, list, preview, detail, relations, and diagram states
- [x] 2.6 Add symptom-specific links from each fallible Getting Started step and verify the complete fresh-checkout journey against the documented commands

## 3. Catalog user journeys

- [x] 3.1 Document catalog navigation, search, filters, pagination, preview panels, favorites or ownership views that are currently supported, and detail-page navigation
- [x] 3.2 Document entity detail pages, owners, systems, derived relations, declared architecture relationships, documentation content, links, and status indicators
- [x] 3.3 Document manual creation and editing for Systems, Components, Resources, APIs, Teams, and other currently supported manual kinds, including required permissions and verification
- [x] 3.4 Document the differences between manual, YAML-managed, unavailable, active, and removed entities and link each state to its lifecycle concept
- [x] 3.5 Document repository registration, `catalog-info.yaml` discovery, ingestion execution, run status, and successful reconciliation
- [x] 3.6 Document ingestion validation failures, claim conflicts, adoption, repository unregistration constraints, retries, and safe corrective actions
- [x] 3.7 Document Remove, Revive, Delete, and Purge eligibility, permissions, reference blockers, preservation behavior, irreversible effects, and verification
- [x] 3.8 Add task-oriented links from catalog workflows to APIs, C4 diagrams, database schemas, flows, and the relevant generated HTTP API operations

## 4. Operator, authentication, and distribution journeys

- [x] 4.1 Expand Operating Atlas with a supported-topology overview and a production-like preflight checklist covering secrets, hosts, origins, database state, composition, startup ordering, and health
- [x] 4.2 Restructure configuration documentation into operator tasks plus a field reference that records owner, type, default or required state, secret handling, topology, and related guide
- [x] 4.3 Document local authentication, administrator access, session behavior, and the supported recovery boundary without inventing an undocumented bootstrap path
- [x] 4.4 Document OIDC enablement, issuer and client configuration, identity resolution, group-claim mapping, allowed origins, secret handling, verification, and safe troubleshooting
- [x] 4.5 Expand distribution assembly from manifest authoring through plugin selection, configuration, secret references, lock generation, preflight, image build, and runtime verification
- [x] 4.6 Add a composition-error guide for identity, version, compatibility, dependency, capability, extension-point, route, configuration, cycle, and package-boundary failures
- [x] 4.7 Document plugin enablement, disablement, removal, reinstallation, preserved data, explicit purge preview and confirmation, and irreversible outcomes
- [x] 4.8 Document database backup, restore, migrations, initializer behavior, migration-safety failures, and post-operation verification using only supported procedures
- [x] 4.9 Add an upgrade guide with preflight, behavior-change review, backup, build and lock updates, migration ordering, smoke checks, and the supported rollback boundary
- [x] 4.10 Move release-specific behavior changes out of the permanent operations procedure into the upgrade or changelog path
- [x] 4.11 Expand troubleshooting by observable symptom across database, initializer, backend, frontend gateway, ingestor, authentication, composition, migration, and rendering failures
- [x] 4.12 Align the root, backend, and frontend READMEs with the canonical site while retaining concise, executable repository-entry commands and safe local reset instructions

## 5. Features and integrations

- [x] 5.1 Create the canonical feature-guide template and machine-readable plugin-id front matter, including explicit not-applicable handling
- [x] 5.2 Expand Standard Catalog into a feature guide covering enablement, kinds, permissions, core user workflows, API surface, operations, extension surface, and limitations
- [x] 5.3 Expand APIs into a feature guide covering API entities, specification sources and refresh, endpoint and operation browsing, service dependencies, permissions, and troubleshooting
- [x] 5.4 Expand C4 into a feature guide covering landscape and entity diagrams, controls and preferences, rendering dependencies, permissions, downloads, and rendering failures
- [x] 5.5 Expand Database Schema into a feature guide covering schema editing, dialects and parse states, ER diagrams, permissions, API behavior, and parse failures
- [x] 5.6 Expand Ingestion into a feature guide covering repositories, scheduling, connectors, parsers, provenance, run history, retries, reconciliation, configuration, and operations
- [x] 5.7 Add the missing `atlas.flows` feature guide covering creation, query/event steps, editing, layout, entity linking, permissions, dependencies, API surface, and limitations
- [x] 5.8 Add a GitHub connector integration guide covering credentials, repository access, configuration, verification, rate or permission failures, and secret handling
- [x] 5.9 Add cross-links from every feature guide to its user tasks, operator procedures, plugin-author extension contracts, concepts, and generated API reference

## 6. Plugin-author journey

- [x] 6.1 Add a decision guide that maps extension needs to Entity Kinds, Facets, Contributions, Capabilities, Extension Points, direct contracts, permissions, and scheduled jobs
- [x] 6.2 Document supported backend-only, frontend-only, and full-stack plugin layouts and the responsibilities of each package and descriptor
- [x] 6.3 Replace the existing first-plugin walkthrough with a source-backed from-scratch tutorial that composes, tests, runs, and visibly verifies a minimal plugin
- [x] 6.4 Preserve the Database Schema walkthrough as an architectural case study and link it from the tutorial at the relevant Facet and contribution decisions
- [x] 6.5 Expand Entity Kind and Facet guidance with lifecycle hooks, data ownership, capabilities, deletion validation, unavailability, and focused tests
- [x] 6.6 Expand frontend contribution guidance for routes, navigation items, entity tabs, home widgets, capability gates, cardinality, and build-time collision failures
- [x] 6.7 Expand backend collaboration guidance for capabilities, extension points, cross-plugin functions, registries, failure isolation, and dependency declarations
- [x] 6.8 Document typed plugin configuration, public projections, secret references, runtime resolution, validation failures, and frontend consumption
- [x] 6.9 Document permission declaration, centralized policy evaluation, resource checks, UI gating, and backend enforcement with tested examples
- [x] 6.10 Document plugin models, migrations, expand-contract constraints, scheduled jobs, startup registration, and safe data lifecycle behavior
- [x] 6.11 Add a testing guide covering Python units, API integration, frontend behavior, composition preflight, migration safety, failure isolation, and compatibility checks with runnable commands
- [x] 6.12 Add a debugging guide organized around import, composition, route, configuration, permission, migration, background-job, API, and frontend contribution failures
- [x] 6.13 Document compatibility ranges, independent core and plugin versioning, packaging, publishing expectations, upgrades, deprecation, disablement, removal, and purge responsibilities
- [x] 6.14 Restructure the Python and TypeScript Plugin API reference so each exact contract is linked from the task or concept that motivates it

## 7. Reference and project documentation

- [x] 7.1 Restructure the `catalog-info.yaml` reference by common envelope, per-kind spec, relationships, validation constraints, complete examples, and links to ingestion tasks
- [x] 7.2 Add exact distribution manifest and lock references covering every supported field, source type, compatibility declaration, configuration shape, and integrity value
- [x] 7.3 Add registries for built-in entity kinds, facets, capabilities, extension points, contribution ids, permissions, scheduled jobs, and owning plugins
- [x] 7.4 Add a management-command reference with prerequisites, side effects, destructive-operation warnings, and links to the workflows that use each command
- [x] 7.5 Expand the authored HTTP API guide with authentication, CSRF, pagination, filtering, errors, representative requests, and links to generated OpenAPI endpoint definitions
- [x] 7.6 Expand Project documentation with repository structure, contribution workflow, local debugging, documentation authoring standards, validation commands, and change review expectations
- [x] 7.7 Add discoverable changelog, versioning and deprecation, ADR, support, and product or technical FAQ entry points, limiting their content to current project policy

## 8. Compatibility and documentation quality gates

- [x] 8.1 Add redirects or maintained legacy entry pages for every moved public URL and update repository links to the canonical targets
- [x] 8.2 Implement the focused documentation validator for page front matter, duplicate plugin ids, default-distribution feature coverage, and navigation inclusion with actionable file-level errors
- [x] 8.3 Configure the clean Zensical build to fail on broken navigation and internal links using strict behavior supported by the existing toolchain
- [x] 8.4 Add parser, formatter, composition, smoke-test, or focused-test validation for every source-backed example introduced by this change
- [x] 8.5 Update the Pages workflow to run the Atlas-specific validator and example checks before the clean site build and publish step
- [x] 8.6 Run documentation validation, build the complete site, inspect all top-level and legacy navigation paths, and fix every reported error or warning
- [x] 8.7 Review the completed site against every specification scenario and the task and feature page contracts, recording any intentionally deferred capability as a separate follow-up rather than a placeholder guide
