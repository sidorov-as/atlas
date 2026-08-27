# Documentation authoring contracts

These contracts apply to new and materially rewritten pages in the expanded
Atlas documentation. They are small enough for hand review and specific enough
for the focused validator (`docs-site/scripts/validate_docs.py`).

## Front matter

Every canonical Markdown page below `docs-site/docs/` must start with YAML
front matter containing these fields:

```yaml
---
title: Create a manual component
description: Add an owner-scoped Component through the Atlas catalog UI.
audience:
  - catalog-user
page-type: task
---
```

| Field | Required value |
| --- | --- |
| `title` | Plain-language page title, unique within its navigation section. It must match the page's H1 wording. |
| `description` | One sentence describing the question answered or outcome produced. Do not repeat the title without adding meaning. |
| `audience` | A non-empty YAML list containing one or more of `evaluator`, `catalog-user`, `operator`, `plugin-author`, or `contributor`. |
| `page-type` | Exactly one of `landing`, `tutorial`, `task`, `feature`, `concept`, or `reference`. |
| `plugin-id` | Required only for `feature`; exactly one id selected by `distributions/default/manifest.yaml`. It is forbidden on other page types. |

Decorative site keys, such as `icon`, may follow the required fields. They are
not part of the content contract. A compatibility page at an old URL uses
`page-type: landing`, declares the canonical destination's audience, contains
no duplicated procedure, and links to the canonical page in its first
paragraph.

Feature example:

```yaml
---
title: Flows
description: Model and inspect multi-step behavior across catalog entities and API operations.
audience:
  - catalog-user
  - operator
  - plugin-author
page-type: feature
plugin-id: atlas.flows
---
```

## Checklist for every page

- [ ] Front matter uses only the controlled values above and the H1 matches
  `title`.
- [ ] The opening paragraph answers why the reader is here before explaining
  internal architecture.
- [ ] Every claim about current behavior has a checked-in source: code, test,
  manifest, configuration, or command.
- [ ] Unsupported, future, and intentionally unavailable behavior is named as
  a limitation; no speculative procedure is presented as supported.
- [ ] Terms agree with the domain glossary and link to the canonical concept
  at the first decision point instead of re-explaining it.
- [ ] Commands identify the working directory/topology and are safe to copy.
  Destructive or secret-bearing operations carry an adjacent warning.
- [ ] Internal links are relative, resolve in a clean site build, and point to
  the canonical page rather than a legacy entry point.
- [ ] Non-trivial examples follow the source-backed example contract below.
- [ ] Screenshots are used only when control location or visual state matters
  and follow the screenshot contract below.
- [ ] The page ends with a verification/result or with links to the tasks that
  apply the material; it does not end at an unexplained implementation detail.

## Section landing page (`landing`)

- [ ] Names the intended audience and the questions the section answers.
- [ ] Identifies the first recommended page or task.
- [ ] Gives an ordered reading path, with optional branches clearly labeled.
- [ ] States the section boundary and links to adjacent journeys instead of
  absorbing their content.
- [ ] Contains no placeholder links or empty child-page summaries.

## Tutorial (`tutorial`)

- [ ] States the starting state, prerequisites, learning outcome, and visible
  final result.
- [ ] Uses one reproducible path from start to finish; optional variations do
  not interrupt the main sequence.
- [ ] Every step says what the reader should observe before continuing.
- [ ] Fallible setup, composition, test, and runtime steps link to the relevant
  symptom-specific diagnostic.
- [ ] Source-backed files compose, test, run, and produce the documented result
  from a fresh supported checkout.
- [ ] The final section verifies the result and offers role-appropriate next
  steps rather than introducing a second tutorial.

## Task guide (`task`)

- [ ] Names the audience and one concrete intended outcome.
- [ ] Lists prerequisites, starting state, required permissions, and any
  topology/plugin assumptions.
- [ ] Gives ordered UI, API, or command steps without mixing alternative
  workflows into a single sequence.
- [ ] States the expected result at material steps and provides a final
  verification independent of a success toast alone.
- [ ] Explains lifecycle, preservation, and irreversible effects before the
  action that causes them.
- [ ] Lists common observable failure symptoms and links each to a safe
  corrective action or focused troubleshooting procedure.
- [ ] Links to the underlying concept at decision points and to the next useful
  task after verification.

## Feature guide (`feature`)

- [ ] `plugin-id` exactly matches one selected default-distribution plugin and
  no other feature guide claims that id.
- [ ] Covers purpose, dependencies, enablement, configuration, permissions,
  primary workflows, API surface, operations, extension surface, limitations,
  compatibility, and troubleshooting.
- [ ] A category that does not apply is written as **Not applicable** with a
  short reason; it is not silently omitted.
- [ ] Links to user tasks, operator procedures, plugin-author contracts,
  concepts, and generated HTTP API operations where applicable.
- [ ] Distinguishes the behavior of an installed, selected, disabled, removed,
  unavailable, and purged plugin or entity where the feature exposes those
  states.
- [ ] Does not imply that optional plugin routes, jobs, or UI contributions
  exist when the plugin is not selected.

## Concept (`concept`)

- [ ] Explains one stable model, vocabulary, or constraint and says why it
  matters.
- [ ] Uses canonical domain terms and distinguishes concepts that are commonly
  confused.
- [ ] Describes invariants and boundaries without embedding a release-specific
  runbook.
- [ ] Links to at least one task or feature guide that applies the concept.
- [ ] Sends exact fields, ids, command flags, and endpoint signatures to the
  appropriate reference unless an abbreviated example is essential.

## Reference (`reference`)

- [ ] Names the authoritative checked-in or generated source and the version or
  runtime scope to which the page applies.
- [ ] Organizes exact fields, ids, values, defaults, constraints, flags, side
  effects, and errors for lookup rather than sequential reading.
- [ ] Is exhaustive for its declared scope, or explicitly links to the
  generated source of truth for the portion it does not reproduce.
- [ ] Generated OpenAPI remains authoritative for endpoint signatures; authored
  HTTP reference explains shared authentication, CSRF, pagination, filtering,
  errors, and representative requests.
- [ ] Links back to the tasks and concepts that give the exact contract context.

## Source-backed examples

### Layout

Non-trivial examples live outside rendered Markdown so repository tools can
parse and test the exact bytes being taught:

```text
docs-site/
  examples/
    <journey-or-feature>/
      <example-id>/
        example.yaml
        <runnable-or-parseable source files>
```

`example.yaml` is the bundle manifest, not an Atlas distribution manifest. It
uses this shape:

```yaml
id: first-plugin-backend
pages:
  - plugin-development/tutorial.md
files:
  - plugin.py
  - tests/test_plugin.py
validation:
  working-directory: core/backend
  command: poetry run pytest ../../docs-site/examples/first-plugin/first-plugin-backend/tests
```

- `id` is unique across `docs-site/examples/` and matches the directory name.
- `pages` contains canonical paths relative to `docs-site/docs/`; at least one
  page must use or link the example.
- `files` lists every authoritative file in the bundle. Generated output and
  secrets are forbidden.
- `validation.working-directory` is relative to the repository root and
  `validation.command` is the exact non-interactive command CI runs from that
  directory.
- An example spanning an existing package may keep its executable fixture and
  test in that package instead. Its bundle then lists those repository-relative
  paths rather than copying them below `docs-site/examples/`.

The current Zensical configuration does not enable a snippet-include extension.
Until an include mechanism is added, a page links to the authoritative example
and may show a short excerpt. A copied non-trivial fence must have a focused
test that compares it with the source. Prose must not imply that an unvalidated
fence is the checked-in runnable file.

### Applicable validators

Run commands from the stated working directory. Replace angle-bracket tokens
with the exact bundle path/package/test recorded in `example.yaml`; committed
bundle manifests must not contain unresolved tokens.

| Example kind | Required validation command | Additional rule |
| --- | --- | --- |
| YAML syntax | From `core/backend`: `poetry run python -c "from pathlib import Path; import yaml; yaml.safe_load(Path('<repo-relative-file>').read_text())"` | Syntax parsing is only the floor. Catalog manifests also run the focused Ingestion parser test; distribution files use `atlas-compose` below. |
| Python | From `core/backend`: `poetry run ruff check <paths>` and `poetry run ruff format --check <paths>`; then `poetry run pytest <focused-test-path>` | The focused test must import or execute the authoritative example, not paste a second copy into the test. |
| TypeScript / TSX | From the repository root: `npm run lint --workspace <workspace>` and `npm run build --workspace <workspace>`; behavior examples also run `npm test --workspace <workspace> -- <focused-test-file>` | Keep the example in a declared npm workspace or test it through one; `tsc`/Vite build must type-check the same file shown to readers. |
| Shell | From the repository root: `bash -n <script>` followed by the bundle's safe smoke test | Scripts start with `set -euo pipefail`, contain no real secret, and make destructive behavior opt-in. Syntax-only validation is insufficient for commands that claim an observable result. |
| `.env` / Compose configuration | From the repository root: `docker compose --env-file <env-file> -f <compose-file> config --quiet` | Validate once per topology the example claims to support. Use placeholders for secrets, never working credentials. |
| Distribution manifest and lock | From `core/backend`: `poetry run atlas-compose validate ../../<manifest> ../../<lock>` | A manifest-only tutorial step also runs `atlas-compose resolve` to a temporary output and compares the expected lock facts without overwriting the checked-in lock. |
| Zensical/TOML/navigation configuration | From `docs-site`: `uv run zensical build --clean` | The clean build is required after navigation, Markdown extension, or site configuration examples change. |

An example that falls into more than one row runs every applicable check. For
example, a distribution manifest is YAML, and `atlas-compose validate` is the
semantic gate; `yaml.safe_load` alone cannot replace it. The bundle commands are
wired into the repository-owned documentation validation entry
point, which Pages CI runs.

## Screenshot capture contract

Screenshots explain control location, spatial relationships, or a material UI
state. Do not use them to decorate a command sequence or repeat text that is
clear without an image.

### Reproduce the data state

Use a clean development topology and the checked-in booking demo seed. From
the repository root:

```shell
docker compose --env-file core/backend/.env -f docker-compose.dev.yml up --build
docker compose --env-file core/backend/.env -f docker-compose.dev.yml exec backend python manage.py migrate
docker compose --env-file core/backend/.env -f docker-compose.dev.yml exec backend python manage.py seed_booking_demo --yes
```

The final command is destructive: it flushes the current database before
recreating the demo. Never run it against a database whose data must be kept.
Use the seeded local administrator only for the capture session, and keep
credentials, cookies, browser extensions, personal accounts, and host-specific
paths out of every frame.

The initial visual tour uses these stable seeded subjects:

| View | Route/action | Required visible state |
| --- | --- | --- |
| Home | `/` | Configured Atlas identity and the complete seeded System Landscape after rendering finishes. |
| List | `/systems` | Default unfiltered active Systems list, sorted by name, including `Search & Discovery`. |
| Preview | Select `Search & Discovery` from the Systems list | Preview panel fully loaded with owner and descriptive metadata; no hover-only control. |
| Detail | Open `Booking & Reservations` | Overview loaded with owner, documentation, and related catalog facts. |
| Relations | Open the Relations tab for `Booking & Reservations` | Derived catalog relations and declared architecture relationships visible in their distinct sections. |
| Diagram | Open System Context for `Booking & Reservations` | Diagram finished, fitted to the viewport, settings panel closed, no loading indicator. |
| APIs list | `/apis` | Default unfiltered APIs list, sorted by name, including the openapi `Booking API`. |
| API spec | Open the Specification tab for `Booking API` | Embedded spec viewer finished rendering the imported OpenAPI contract. |
| API operation | Open `GET /bookings/{id}` under `Booking API` | Operation Overview loaded with details and its linked-services graph finished loading. |
| Flow | Open the Flow tab for `notification-delivery-flow` | Graph finished loading and fitted to the viewport. |
| ER Diagram | Open the ER Diagram tab for `Booking DB` | Parsed schema graph finished loading and fitted to the viewport. |
| System Map | `/system-map` | Diagram finished, fitted to the viewport, settings panel closed, no loading indicator. |

Random database UUIDs and timestamps are outside the visual contract. Do not
show the address bar or name assets after generated ids. If a guide needs a
failure, removed, or filtered state that the seed does not produce immediately,
its capture note must record the exact supported UI/API steps used after
seeding.

### Capture settings

- **Viewport:** desktop captures use a 1440 x 900 CSS-pixel viewport at 100%
  browser zoom and device-pixel ratio 1. A responsive instruction may add one
  390 x 844 mobile capture, but never substitutes it for the desktop baseline.
- **Theme:** use Atlas light theme for the baseline. Add a dark-theme variant
  only when the page teaches theme behavior or the control is materially
  different. Record the chosen theme in the filename.
- **Data:** reseed immediately before a capture set. Clear search/filter state
  unless the screenshot teaches that state; then record the exact query and
  filters in the page's source comment.
- **Timing:** wait for requests, fonts, preview content, and diagrams to finish.
  Remove focus rings or hover state unless they are the behavior being taught.
- **Framing:** capture the smallest complete application region that preserves
  orientation. Exclude browser chrome, desktop wallpaper, terminals, and
  unrelated blank space.
- **Format:** store UI captures as PNG below
  `docs-site/docs/assets/screenshots/<journey>/`. Do not commit Retina-sized
  duplicates when the DPR-1 image is legible.

### Filename and alt text

Use lowercase kebab case:

```text
<journey>-<subject>-<view>-<state>-<theme>.png
```

Omit only `state` when the view has no meaningful variant. Examples:

- `getting-started-systems-list-active-light.png`
- `getting-started-search-discovery-preview-light.png`
- `getting-started-booking-reservations-relations-light.png`
- `getting-started-booking-reservations-context-diagram-light.png`

Names never contain a timestamp, random UUID, author's name, `final`, or
`screenshot`. Replace an existing asset in place when its documented state is
unchanged so links remain stable.

Alt text describes the information a reader needs from the image. Name the
page or control, selected entity, and material state or relationship. Avoid
“image of” and “screenshot of.” For example:

```markdown
![Booking & Reservations Relations tab separating derived catalog relations from declared architecture relationships.](../assets/screenshots/getting-started/getting-started-booking-reservations-relations-light.png)
```

If surrounding prose already communicates every fact in the image, use empty
alt text only when the image is genuinely decorative; most instructional UI
captures are not.

### Capture review checklist

- [ ] The source commit includes the exact demo seed used for capture, and the
  PR records that commit SHA in its verification notes.
- [ ] Viewport, DPR, zoom, theme, route, entity, filters, and any post-seed
  mutation match this contract or are recorded next to the image reference.
- [ ] The UI is fully loaded, legible at rendered documentation width, and free
  of transient toasts unless the toast itself is being explained.
- [ ] Filename and asset directory identify the canonical journey and stable
  state without generated ids.
- [ ] Alt text communicates the instructional content and agrees with the
  current UI labels.
- [ ] No secret, session token, real account, private repository, local path,
  or unrelated browser/desktop content is visible.
- [ ] The page states what the reader should notice and does not rely on color
  alone to distinguish status or action.
- [ ] A clean Zensical build resolves the asset path.

### Recapture triggers

Recapture an affected asset when any of the following changes what the image
shows or what its instruction asks the reader to find:

- the demo seed's named entities, metadata, relations, API documents, schemas,
  flows, tags, or initial lifecycle state;
- navigation labels/order, route ownership, page layout, component structure,
  control labels/icons, tabs, tables, previews, forms, diagrams, or empty/error
  states;
- theme tokens, typography, spacing, status treatment, accessibility labels, or
  the baseline viewport/theme contract;
- permissions or feature composition that hides, exposes, enables, or disables
  a captured action;
- the documented steps, selected subject, filter/query, or expected result.

Do not recapture for a backend refactor, test-only change, or copy edit that
does not change the visible state or instructional meaning. The reviewer must
still mark existing assets as reviewed when a recapture trigger affects the
change.
