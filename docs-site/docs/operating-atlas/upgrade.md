---
title: Upgrade an Atlas distribution
description: Safely prepare, compose, deploy, and verify an Atlas upgrade within the supported recovery boundary.
audience:
  - operator
page-type: how-to
---

# Upgrade an Atlas distribution

## Prerequisites

- A tested database backup/restore procedure outside this repository's scope.
- Release notes or the project changelog for the exact versions being changed.
- A reviewed manifest change and an available maintenance window when schema compatibility requires it.

## Procedure

1. Review behavior changes and plugin/core compatibility ranges. Treat plugin selection, disabling, and removal as product changes.
2. Back up data using your database platform's tested procedure. The repository has no generic restore command.
3. Update the manifest versions/configuration and generate a fresh lock.
4. Run `atlas-compose validate` on the manifest and lock, then build the immutable distribution image.
5. Start with the supported topology. Allow `postgres` to become healthy, followed by `initializer` migrations, then the backend and gateway.
6. Smoke-test `/healthz/`, `/healthz/plugins/`, login, and a representative catalog read. Test a feature changed by a selected plugin.

## Known breaking changes

- **Catalog branding moved from environment variables to a frontend file.**
  The `CATALOG_TITLE`/`CATALOG_DESCRIPTION` environment variables and the
  backend `GET /api/catalog-configuration/` endpoint are removed. A
  deployment that set either variable stops having any effect after
  upgrading. The frontend now sources title, tagline, logo, and icon from
  `core/frontend/src/atlas.config.ts`, a committed file rebuilt with the
  frontend image. See [Catalog branding](../configuration/catalog-branding.md)
  to set the replacement before or alongside this upgrade.

## Rollback boundary

Atlas's migration safety rules support expand-contract rollout constraints. They do not provide an automatic schema downgrade or a guaranteed rollback to an arbitrary version. Roll back only to a version compatible with the current database schema, or restore the database through your independently tested platform procedure. Do not reverse migration records manually.

Keep release-specific behavior in release notes and the project changelog. Use [data safety](data-safety.md) and [troubleshooting](../deployment/troubleshooting.md) when a step fails.

If any Principal has an assigned read-only account restriction, rollback is additionally
security-sensitive: a version that ignores `AccountAccess` restores write privileges. Preserve an
equivalent guard or block/deactivate every affected account before old code serves requests, and
preserve the side-car and audit data across migration changes. Follow the complete [read-only
rollback procedure](read-only-accounts.md#security-sensitive-rollback).

Authentication upgrades that cross the authoritative-selection boundary also
require manifest edits, a regenerated lock, closed-signup verification, source
review, legacy-grant classification, and fallback testing. An older build that
ignores revocation/source generations or finite grant freshness is not a safe
online rollback target. Follow the [authentication migration and revocation
runbook](authentication-migration.md).
