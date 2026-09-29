## Purpose

APIs is the optional plugin that provides the `api` Entity Kind, extracted out of Standard Catalog so a distribution can omit it. It declares a manifest dependency on Standard Catalog (Components reference APIs via `providesApis`/`consumesApis`), and Standard Catalog degrades gracefully — validating those reference fields as empty rather than erroring — when APIs is not selected.

## Requirements

### Requirement: API is an optional plugin-provided kind
The API Entity Kind SHALL be provided entirely by the `atlas.apis` plugin; a distribution MAY omit it.

#### Scenario: Distribution without atlas.apis composes successfully
- **WHEN** a distribution selects `atlas.standard-catalog` but not `atlas.apis`
- **THEN** composition succeeds, and no `api` kind is registered

### Requirement: APIs plugin declares a manifest dependency on Standard Catalog
`atlas.apis` SHALL declare a manifest dependency on `atlas.standard-catalog` within a compatible version range; composition SHALL fail if that dependency isn't satisfied.

#### Scenario: Compatible Standard Catalog satisfies the dependency
- **WHEN** a distribution selects `atlas.apis` and a version of `atlas.standard-catalog` within its declared compatible range
- **THEN** composition succeeds

### Requirement: Cross-plugin API references degrade gracefully when APIs is absent
Standard Catalog's `providesApis`/`consumesApis` reference fields SHALL be valid and empty, not an error, when `atlas.apis` is not selected.

#### Scenario: providesApis is inert without the APIs plugin
- **WHEN** `atlas.apis` is not selected
- **THEN** a Component's `providesApis`/`consumesApis` fields accept no values and any pre-existing values are treated as referencing an absent kind, without crashing the Component's own CRUD or detail page
