---
title: Feature guide template
description: Review contract for a canonical Atlas feature guide.
audience: [plugin-author]
page-type: reference
plugin-id: not-applicable
---

# Feature guide template

Use this template for the one canonical guide for a plugin selected by a
distribution. `plugin-id` is required for a plugin guide and must exactly match
the descriptor id (for example, `atlas.flows`). A page that documents an
integration rather than a plugin uses `plugin-id: not-applicable`.

Each guide covers the sections below. Write `Not applicable` when the
installed feature has no configuration, permissions, API, operational behavior,
or extension surface. Do not omit the category.

## Required front matter

```yaml
---
title: Human-readable feature name
description: What the installed feature lets a reader do.
audience: [catalog-user, operator, plugin-author]
page-type: feature
plugin-id: atlas.example
---
```

## Required content contract

1. Purpose and dependencies: describe the installed behavior, required plugins,
   and capability gates.
2. Enablement and configuration: document distribution selection,
   configuration keys, and secret handling. Write `Not applicable` if no
   settings exist.
3. Permissions: list the permission names and the resource or ownership rule.
4. User workflows: show concrete UI or API paths, their expected results, and
   links to the general catalog task guides.
5. API surface: provide a short description and a link to the running generated
   API reference. Do not duplicate endpoint signatures.
6. Operations: document jobs, data lifecycle, dependencies, health concerns, or
   write `Not applicable`.
7. Extension surface: document supported contracts and links for authors, or
   write `Not applicable`.
8. Limitations, compatibility, and troubleshooting: cover the supported
   boundary, compatibility dependencies, observable failures, and corrective
   actions.
9. Next steps: link to the relevant user task, operator procedure, concepts,
   plugin-author contract, and generated HTTP API.
