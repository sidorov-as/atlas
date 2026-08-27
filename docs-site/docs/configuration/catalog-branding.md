---
title: Catalog branding
description: Set your deployment's title, tagline, logo, and icon via atlas.config.ts.
audience:
  - operator
page-type: reference
---

# Catalog branding

Atlas sources a deployment's identity — title, tagline, logo, and icon — from
a single committed frontend file: `core/frontend/src/atlas.config.ts`.

```ts
export const atlasConfig: AtlasConfig = {
  title: 'Atlas',
  tagline: 'A software catalog for teams, systems, components, resources, and APIs.',
  logo: '/atlas-logo.svg',
  icon: '/favicon.ico',
}
```

- `title` and `logo` appear in the application shell's sidebar header.
- `title` and `tagline` appear on the homepage, above the entity-kind counts
  and the "About this catalog" section.
- `logo` and `icon` are paths served from `core/frontend/public/`; replace the
  referenced file (or point to a new one you add there) to change the image.

## Changing branding

Edit `atlas.config.ts` and rebuild the frontend. There is no environment
variable, database record, or running-deployment toggle for these values —
branding is deploy-time identity, set once per build, not editable at
runtime. This also means `atlas.config.ts` cannot be overridden per
distribution without forking Core's frontend source; this is a deliberate
limitation given Core's own independent versioning and distribution model,
revisited if external, non-forked distributions become a real need.

## Related: "About this catalog"

The homepage's longer-form "About this catalog" Markdown section is a
separate, admin-editable concept — a `CatalogHomeSettings` database record,
not part of `atlas.config.ts`. A superuser edits it from **Settings → Home**
in the running application; see [Using Atlas](../using-atlas/index.md).

## Migrating from `CATALOG_TITLE`/`CATALOG_DESCRIPTION`

Earlier Atlas versions read the homepage's title and description from the
`CATALOG_TITLE`/`CATALOG_DESCRIPTION` environment variables via a backend
`GET /api/catalog-configuration/` endpoint. Both the environment variables
and the endpoint are removed. Set `title`/`tagline` in `atlas.config.ts`
instead. See [Upgrade an Atlas distribution](../operating-atlas/upgrade.md)
for the full breaking-change note.
