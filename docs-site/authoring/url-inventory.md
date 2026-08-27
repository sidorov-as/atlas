# Documentation URL inventory

Baseline captured on 2026-09-12 from `docs-site/docs/**/*.md` and the
navigation in `docs-site/zensical.toml`. The published site base is
`https://sidorov-as.github.io/atlas/`. The table records paths below that base
and accounts for all 29 Markdown pages present at the baseline.

## Classification rules

- **Keep**: the current page remains the canonical page at the same URL.
- **Expand**: the current URL remains canonical, but its content must grow to
  satisfy the new page contract or capability coverage.
- **Move**: the content receives a new canonical URL. The current URL must be
  retained as a redirect or thin legacy entry page.
- **Replace**: the current URL stays public but serves a different reader
  purpose after the information-architecture change.
- **Legacy entry point**: the current page becomes only a compatibility route
  to the listed canonical page. It must not retain a second copy of the
  canonical content.

## Current pages and migration decisions

| Source | Current URL | Classification | Canonical target | Reason |
| --- | --- | --- | --- | --- |
| `docs-site/docs/index.md` | `/` | Replace | `/` | Replace the setup-first page with the audience-oriented home page; route setup readers to `/getting-started/`. |
| `docs-site/docs/deployment/index.md` | `/deployment/` | Legacy entry point | `/operating-atlas/` | Deployment becomes one part of the operator journey. |
| `docs-site/docs/deployment/development.md` | `/deployment/development/` | Keep | `/deployment/development/` | Reference for the source-mounted topology's services and ports; the first-run walkthrough lives at `/getting-started/development/`. |
| `docs-site/docs/deployment/production.md` | `/deployment/production/` | Move | `/operating-atlas/production-like/` | Production-like setup belongs to the operator journey. |
| `docs-site/docs/deployment/operations.md` | `/deployment/operations/` | Move | `/operating-atlas/operations/` | Migrations, logs, shutdown, and recovery are operator tasks. |
| `docs-site/docs/deployment/troubleshooting.md` | `/deployment/troubleshooting/` | Move | `/operating-atlas/troubleshooting/` | Troubleshooting becomes symptom-oriented and spans all runtime services. |
| `docs-site/docs/configuration/environment-variables.md` | `/configuration/environment-variables/` | Move | `/reference/configuration/` | Exact fields belong in Reference; operator guides link to the relevant rows. |
| `docs-site/docs/configuration/distributions.md` | `/configuration/distributions/` | Move | `/operating-atlas/distributions/` | Distribution assembly is an end-to-end operator workflow. |
| `docs-site/docs/concepts/glossary.md` | `/concepts/glossary/` | Keep | `/concepts/glossary/` | The existing domain vocabulary remains canonical. |
| `docs-site/docs/concepts/entity-model.md` | `/concepts/entity-model/` | Keep | `/concepts/entity-model/` | The conceptual model is sound and is linked from task guides. |
| `docs-site/docs/concepts/entity-references.md` | `/concepts/entity-references/` | Keep | `/concepts/entity-references/` | Reference and relationship semantics remain canonical here. |
| `docs-site/docs/concepts/catalog-info-yaml.md` | `/concepts/catalog-info-yaml/` | Move | `/reference/catalog-info-yaml/` | The page is a field-and-kind reference, not a concept page. |
| `docs-site/docs/concepts/life-of-an-entity.md` | `/concepts/life-of-an-entity/` | Expand | `/concepts/life-of-an-entity/` | Retain the lifecycle model and add task links for every state transition. |
| `docs-site/docs/concepts/auth-and-identity.md` | `/concepts/auth-and-identity/` | Expand | `/concepts/auth-and-identity/` | Retain the model and link it to local and OIDC operator procedures. |
| `docs-site/docs/concepts/permissions.md` | `/concepts/permissions/` | Expand | `/concepts/permissions/` | Retain authorization concepts and link exact ids to the permission registry. |
| `docs-site/docs/concepts/system-shape.md` | `/concepts/system-shape/` | Keep | `/concepts/system-shape/` | The supported runtime and ownership boundary remains canonical. |
| `docs-site/docs/concepts/principles.md` | `/concepts/principles/` | Keep | `/concepts/principles/` | The architectural constraints remain canonical. |
| `docs-site/docs/plugin-development/index.md` | `/plugin-development/` | Expand | `/plugin-development/` | Keep the established entry point and turn it into an ordered author journey. |
| `docs-site/docs/plugin-development/tutorial.md` | `/plugin-development/tutorial/` | Replace | `/plugin-development/tutorial/` | Replace the existing-plugin tour with a source-backed from-scratch tutorial. |
| `docs-site/docs/plugin-development/extension-points.md` | `/plugin-development/extension-points/` | Expand | `/plugin-development/extension-points/` | Add decision guidance, direct contracts, failure isolation, and tests. |
| `docs-site/docs/plugin-development/entity-kinds-and-facets.md` | `/plugin-development/entity-kinds-and-facets/` | Expand | `/plugin-development/entity-kinds-and-facets/` | Add lifecycle hooks, ownership, deletion validation, and focused tests. |
| `docs-site/docs/plugin-development/reference.md` | `/plugin-development/reference/` | Move | `/reference/plugin-api/` | Exact Python and TypeScript contracts belong in Reference. |
| `docs-site/docs/plugin-development/built-in/standard-catalog.md` | `/plugin-development/built-in/standard-catalog/` | Legacy entry point | `/features/standard-catalog/` | Product use becomes canonical; the developer URL remains compatible. |
| `docs-site/docs/plugin-development/built-in/apis.md` | `/plugin-development/built-in/apis/` | Legacy entry point | `/features/apis/` | Product use becomes canonical; the developer URL remains compatible. |
| `docs-site/docs/plugin-development/built-in/c4.md` | `/plugin-development/built-in/c4/` | Legacy entry point | `/features/c4/` | Product use becomes canonical; the developer URL remains compatible. |
| `docs-site/docs/plugin-development/built-in/database-schema.md` | `/plugin-development/built-in/database-schema/` | Legacy entry point | `/features/database-schema/` | Product use becomes canonical; the developer URL remains compatible. |
| `docs-site/docs/plugin-development/built-in/ingestion.md` | `/plugin-development/built-in/ingestion/` | Legacy entry point | `/features/ingestion/` | Product use becomes canonical; the developer URL remains compatible. |
| `docs-site/docs/api-reference/index.md` | `/api-reference/` | Expand | `/api-reference/` | Preserve the established URL while adding authored HTTP conventions and generated-reference links. |
| `docs-site/docs/contributing/index.md` | `/contributing/` | Move | `/project/contributing/` | Contribution guidance becomes part of the broader Project section. |

## Migration invariants

1. Every **Move** and **Legacy entry point** row keeps its current URL through
   a redirect supported by the site tool or a maintained one-screen Markdown
   entry page.
2. A legacy page names and links to one canonical target; it does not mirror
   the target's procedure or reference tables.
3. Repository links are updated to canonical targets in the same change that
   creates those targets.
4. Navigation validation must cover the current and canonical paths until the
   migration is complete.
