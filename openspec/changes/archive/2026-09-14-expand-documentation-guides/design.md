## Context

The current Zensical site contains 29 Markdown pages. Its strongest material is
the conceptual core (`concepts/`) and the plugin contract explanation, while
its navigation is organized primarily around internal system areas. Catalog
users have no dedicated guide, operator material stops at a small Compose
runbook, built-in plugins are documented as developer notes, and the plugin
tutorial explains an existing implementation instead of producing a plugin
from an empty package.

Atlas now exposes enough catalog, ingestion, distribution, authentication,
plugin-lifecycle, API, diagram, database-schema, and flow behavior that readers
need task-oriented paths through those capabilities. The documentation must
remain grounded in checked-in behavior and must not imply support for deployment
targets, integrations, or lifecycle guarantees that do not exist.

The main stakeholders are:

- evaluators who need to understand Atlas and reach a useful local result;
- catalog users and maintainers who manage entities and repositories;
- operators who configure, compose, deploy, upgrade, and recover Atlas;
- plugin authors who extend a distribution safely;
- contributors who maintain Atlas and its documentation.

The site already builds in the Pages workflow with `uv run zensical build
--clean`. This change retains that toolchain and adds documentation-specific
validation around it.

## Goals / Non-Goals

**Goals:**

- Make each primary audience and its first task visible from the home page.
- Cover the supported end-to-end user, operator, distribution, and plugin-author
  journeys agreed in the proposal and specs.
- Preserve and reuse the existing conceptual material instead of rewriting it
  for every tutorial.
- Give feature and task pages predictable structures that expose prerequisites,
  permissions, outcomes, verification, and failure modes.
- Keep examples, navigation, plugin coverage, and internal links verifiable in
  CI.
- Migrate without breaking existing documentation entry points.

**Non-Goals:**

- Change Atlas runtime behavior, APIs, plugin contracts, or deployment support.
- Document Kubernetes, horizontal scaling, provider integrations, publishing
  infrastructure, or other capabilities before the repository supports them.
- Copy Backstage's page count or reproduce reference projects' content.
- Hand-author endpoint signatures that belong to generated OpenAPI reference.
- Introduce versioned documentation or automated screenshot capture in this
  change.

## Decisions

### 1. Organize the site by reader intent

The primary navigation will be:

```text
Overview
Getting Started
Using Atlas
Operating Atlas
Features & Integrations
Concepts & Architecture
Plugin Development
Reference
Project
```

Each section gets a landing page that names its audience, scope, entry task,
and recommended reading order. The home page routes readers by role and starts
with the useful outcome they can obtain, rather than presenting the repository
or service topology first.

Alternative considered: retain the current navigation and append more pages.
That reduces file movement but leaves task guides scattered between deployment,
configuration, concepts, and plugin development, which is the current
discoverability problem.

### 2. Treat tutorials, how-to guides, concepts, and references as different page types

The site will use four content types:

- tutorials lead a reader through a complete learning journey;
- how-to guides solve one concrete task;
- concepts explain models and design constraints;
- references provide exact fields, identifiers, commands, and API contracts.

Task pages will use a shared authoring checklist: audience, prerequisites,
outcome, permissions, ordered steps, verification, common failures, and next
steps. Feature pages will use a second checklist: plugin id, purpose,
dependencies, enablement, configuration, permissions, workflows, API,
operations, extension surface, limitations, compatibility, and
troubleshooting. A category that does not apply is marked explicitly instead
of silently omitted.

Alternative considered: one universal template. It produces mechanical pages
and forces irrelevant sections onto concepts and references; two focused
contracts plus lightweight concept/reference conventions are easier to review.

### 3. Keep concepts canonical and link tasks to them

Existing concept pages remain the canonical explanation of entity identity,
references, lifecycle, claims, permissions, and plugin composition. Tutorials
and how-to pages explain what a reader must do and link to the relevant concept
at the decision point. They do not duplicate the full conceptual model.

The root and component READMEs follow the same rule: they retain short commands
needed at repository entry points and link to the canonical site for the full
walkthrough, operations, and recovery procedures.

Alternative considered: make every tutorial self-contained. That would be
convenient for a single reading but would create multiple copies of security,
lifecycle, and deployment rules that can drift independently.

### 4. Separate feature use from plugin implementation

Built-in plugin pages move conceptually from Plugin Development to Features and
Integrations. Their canonical feature guides describe the installed product;
Plugin Development links to the same guides only for implementation examples.
The existing `plugin-development/built-in/*` URLs are preserved through
redirects or thin legacy entry pages if the site tool cannot emit redirects.

Each canonical feature page carries machine-readable front matter with its
Atlas plugin id. A focused documentation validator compares those ids with
`distributions/default/manifest.yaml` and ensures every selected plugin has
exactly one navigated feature guide. This closes the class of drift that left
`atlas.flows` undocumented.

Alternative considered: manually maintain a feature checklist. Machine-readable
coverage is small to implement and detects drift at the change that introduces
it.

### 5. Build content in vertical journeys, not directory-sized batches

Implementation proceeds through complete reader journeys:

1. navigation, landing pages, and first useful catalog result;
2. catalog use and ingestion;
3. operator, authentication, distribution, upgrade, and recovery guides;
4. feature guides for every default plugin;
5. plugin-author decision guide, tutorial, testing, and debugging;
6. layered reference and project documentation;
7. redirects, README alignment, assets, and final quality validation.

Each journey includes its navigation, cross-links, verification, and
troubleshooting before the next begins. This lets reviewers assess usable
increments and prevents a polished hierarchy containing placeholder pages.

Alternative considered: create the entire directory tree first and fill it
section by section. That makes navigation appear complete before any audience
can finish a real task.

### 6. Ground UI guidance and examples in reproducible repository state

UI walkthroughs use the checked-in demo seed where possible. Screenshots are
stored below `docs-site/docs/assets/`, have descriptive alt text, and are used
when the location or visual state of a control matters. Pure command sequences
do not receive decorative screenshots.

Non-trivial YAML, Python, TypeScript, shell, and configuration examples are
kept as checked-in source-backed examples or focused fixtures when practical.
The documentation includes them through a mechanism supported by the existing
Zensical/Markdown toolchain, or validation targets the exact checked-in example
when inclusion is unavailable. Applicable parsers, formatters, composition
checks, or focused tests run against those sources.

Alternative considered: copy code blocks directly into every page. It is
simpler initially but cannot detect examples drifting from schemas and public
contracts.

### 7. Extend the existing documentation build with focused quality gates

The Pages workflow remains the publishing path. Its validation stage will:

- run a clean site build and treat navigation or internal-link warnings as
  failures where the toolchain supports strict mode;
- run a small repository-owned validator for required front matter, default
  distribution feature coverage, duplicate plugin ids, and navigation
  inclusion;
- run the applicable checks for source-backed examples;
- verify that legacy entry points resolve to canonical pages.

The focused validator will report the source file and failed contract rather
than only returning a generic build error. External links are not made a hard
publishing dependency because remote availability is outside the repository's
control.

Alternative considered: add a broad third-party documentation linter. The
existing build plus small Atlas-specific checks provides clearer failures and
avoids a new policy surface unrelated to the requirements.

### 8. Preserve URLs and separate navigation migration from file movement

Navigation can point at an existing high-quality page without moving it solely
to match the sidebar. New pages use directories matching the new sections.
Files move only when ownership changes materially, such as canonical built-in
plugin guides moving to Features. Each move is accompanied by a redirect or
legacy entry page, and all repository links are updated to the canonical path.

Alternative considered: move every current file into a matching new directory
in one commit. That creates noisy diffs, obscures content review, and breaks
external links for no reader-visible gain.

## Risks / Trade-offs

- [Scope expands into a rewrite of every page] → Implement the specified
  vertical journeys in priority order, reuse sound concept pages, and avoid
  prose-only rewrites without a scenario or correctness benefit.
- [Documentation promises unsupported production capabilities] → Derive guides
  from current code, tests, manifests, and OpenSpec requirements; label current
  limits explicitly and omit speculative procedures.
- [Screenshots become stale] → Use them only when visual location matters,
  capture them from the seeded demo, keep a capture checklist, and require
  screenshot review when affected UI changes.
- [Source-backed examples add maintenance overhead] → Apply them to examples
  with schema, syntax, or security risk; keep short illustrative fragments
  inline when validation would add no value.
- [URL preservation constrains cleaner directories] → Prefer stable reader
  entry points over filesystem symmetry; use canonical links and thin redirects
  to prevent duplicate content.
- [Documentation validator duplicates site-tool behavior] → Limit custom checks
  to Atlas-specific contracts and delegate normal Markdown rendering and link
  resolution to Zensical.
- [One large change is difficult to review] → Keep tasks and commits grouped by
  complete audience journeys, with a clean site build after each group.

## Migration Plan

1. Record the current URL inventory and map each page to keep, expand, move, or
   replace.
2. Add page contracts, the target navigation, and section landing pages while
   retaining links to existing canonical content.
3. Complete the Getting Started and Using Atlas journeys and their UI assets.
4. Complete Operating Atlas, distribution, authentication, upgrade, and
   troubleshooting journeys; align root and component README links.
5. Publish canonical feature guides for all default plugins, including Flows,
   and install compatibility entry points for moved built-in pages.
6. Complete the plugin-author, reference, and project sections with validated
   examples.
7. Enable strict build and Atlas-specific documentation checks in CI, repair
   every reported link or coverage gap, and perform a final navigation and
   scenario review.

Rollback is content-only: revert the navigation and new pages while retaining
legacy URLs. No runtime data or API migration is involved.

## Open Questions

No question blocks implementation. Versioned documentation and automated
screenshot capture are intentionally deferred; they can be proposed separately
if release cadence or UI churn makes them necessary.
