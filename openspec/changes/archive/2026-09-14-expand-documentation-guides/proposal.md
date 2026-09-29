## Why

Atlas's documentation explains its domain model and plugin architecture, but it
does not yet guide catalog users, operators, and plugin authors through the
tasks they need to complete. As the product surface grows, the missing
task-oriented layer is already causing discoverability gaps and documentation
drift, such as the default Flows plugin having no feature guide.

## What Changes

- Reorganize the documentation site around explicit reader journeys: overview,
  getting started, using Atlas, operating Atlas, features and integrations,
  concepts and architecture, plugin development, reference, and project
  documentation.
- Add end-to-end guides for the first useful catalog experience, everyday
  catalog management, repository registration and ingestion, authentication,
  distribution assembly, production operations, upgrades, and troubleshooting.
- Turn built-in plugin notes into consistent feature guides that cover purpose,
  enablement, configuration, permissions, user workflows, API surface,
  operations, extension points, limitations, and troubleshooting; add the
  missing Flows guide.
- Expand plugin-author documentation from an architectural walkthrough into a
  from-scratch, testable path covering plugin shape, backend and frontend
  contributions, configuration and secrets, permissions, persistence,
  background jobs, composition, debugging, compatibility, and publishing.
- Establish reusable page templates, audience labels, prerequisites, expected
  results, verification steps, failure modes, screenshots where UI state is
  material, and source-backed code examples.
- Clarify the boundary between concise repository READMEs and the canonical
  documentation site, with links that keep all supported launch paths
  discoverable without maintaining conflicting copies.
- Preserve existing public documentation URLs where practical and add redirects
  for pages moved by the new information architecture.

## Capabilities

### New Capabilities

- `documentation-site-experience`: Audience-oriented information architecture,
  task-based guides, feature and plugin-author content contracts, navigation,
  cross-linking, examples, and documentation quality controls.

### Modified Capabilities

- `developer-launch-documentation`: Define the repository README as the concise
  launch entry point and the documentation site as the canonical source for
  detailed setup, verification, operations, and recovery guidance.

## Impact

- Primary scope: `docs-site/docs/` and `docs-site/zensical.toml`.
- Supporting scope: root and component READMEs, documentation assets, example
  sources, redirect configuration, and documentation validation in CI.
- Runtime application behavior and public APIs are unchanged; documentation
  examples and screenshots must describe only capabilities that the repository
  currently supports.
