---
title: Plugin Development
description: Choose an Atlas extension contract and follow the supported path from plugin code to a composed distribution.
audience:
  - plugin-author
page-type: landing
---

# Plugin Development

This section covers extending Atlas through its public Python and TypeScript
contracts. A plugin is a trusted,
operator-selected backend package, frontend package, or pair of packages whose
contributions are composed into a distribution at build time.

## Who this section is for

Use this section if you build or maintain an Atlas plugin. It explains:

- which extension mechanism fits the behavior or data you want to add;
- how Entity Kinds, Facets, frontend Contributions, Capabilities, and Extension
  Points differ;
- how plugin code is selected and validated as part of a distribution; and
- which boundaries keep Core and sibling plugins isolated.

## Start here

If the terms above are new, read the [Domain
glossary](../concepts/glossary.md) first. Then use [Choose an extension
mechanism](choose-an-extension.md) to select the contract that matches your
change before following [Build your first plugin](tutorial.md).

## Recommended path

1. [Domain glossary](../concepts/glossary.md) teaches the shared extension
   vocabulary.
2. [Choose an extension mechanism](choose-an-extension.md) maps your data, UI,
   runtime collaboration, authorization, or background-work need to the
   supported contract.
3. [Build your first plugin](tutorial.md) follows a complete plugin path.
4. [Choose a plugin layout](plugin-layouts.md) helps select a backend-only,
   frontend-only, or full-stack package shape and its responsibilities.
5. [Frontend contributions](extension-points.md) explains how to add routes,
   navigation, detail tabs, and home widgets that compose safely.
6. [Entity kinds and facets](entity-kinds-and-facets.md) covers owned catalog
   kinds and data attached to an existing kind.
7. [Backend collaboration](backend-collaboration.md) covers publishing and
   consuming backend contracts without crossing plugin boundaries.
8. [Authentication provider SDK](authentication-provider-sdk.md) covers
   credential and redirect verification through `atlas.auth.providers.v1`.
9. [Plugin contract reference](reference.md) lists the exact Python and
   TypeScript package surface.
10. [Plugin permissions](permissions.md), [models, migrations, and jobs](models-migrations-and-jobs.md),
   [testing](testing.md), and [debugging](debugging.md) cover how to make,
   validate, and diagnose a safe extension.
11. [Compatibility and lifecycle](compatibility-and-lifecycle.md) explains how
    to prepare a compatible upgrade or removal.
12. [Standard Catalog](../features/standard-catalog.md) and the other built-in
    feature notes show first-party implementations that use the same contracts.

## Section boundary

A plugin cannot import another plugin's models or internal modules, replace
another plugin's contributions, patch Core behavior, or install itself from a
running Atlas instance. Distribution selection and lifecycle procedures belong
in [Operating Atlas](../operating-atlas/index.md); installed product behavior
belongs in [Features and Integrations](../features/index.md).
