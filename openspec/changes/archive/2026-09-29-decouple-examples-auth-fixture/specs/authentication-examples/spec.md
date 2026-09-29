## ADDED Requirements

### Requirement: Examples are self-validating and safely deletable
No requirement, build step, or required check outside `examples/authentication/` and that example's own dedicated CI workflows SHALL depend on the content of a specific authentication example. Each example SHALL validate its own compatibility with the public SDK contract, composer's manifest/lock schemas, and its own documentation through checks that live under `examples/authentication/` and run in that example's own CI workflow(s), triggered both by changes to the example itself and by changes to the upstream surfaces it depends on (the plugin SDK, composer, first-party auth plugins, the docs site).

#### Scenario: An example directory is deleted
- **WHEN** `examples/authentication/custom-credentials` is removed from the repository
- **THEN** the backend's dependency install, both backend Docker images, and the repo-root pytest suite all still succeed; docs-site's fixture-specific accuracy checks (ported to `validate.py`) no longer run there. Cross-reference links in `docs/` and the example's own `README.md` are expected to need updating as part of that deletion, same as any other doc removal — not a build/dependency coupling this requirement covers.

#### Scenario: An upstream contract changes
- **WHEN** the public `atlas_plugin_api` credential-provider contract, a composer schema, or a first-party auth plugin changes in a way the custom credential example no longer matches
- **THEN** the example's own CI workflow fails, independent of whether any file under `examples/authentication/` itself changed
