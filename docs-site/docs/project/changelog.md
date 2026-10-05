---
title: Changelog, versioning, and support
description: Find the project's history and support boundaries without assuming a release policy.
audience: [contributor, operator, plugin-author]
page-type: reference
---

# Changelog, versioning, and support

This repository has no release-by-release changelog, ADR log, support
channel, or formal external compatibility policy. Behavior changes that can
break an existing deployment are listed under [Pre-release behavior
changes](#pre-release-behavior-changes).

Core and plugin versions are declared independently, and distribution
selection is locked at build time. See
[Compatibility and lifecycle](../plugin-development/compatibility-and-lifecycle.md)
for compatibility and deprecation boundaries. Report reproducible repository
issues through the project's normal issue or review workflow. This page does
not promise a support SLA.

## Authentication migration notice

The production authentication change closes anonymous local signup by default
and makes manifest provider selection authoritative. Existing local-only and
experimental OIDC deployments must add explicit provider objects and a selected
default, regenerate their lock, and verify fallback before rollout. OIDC
deployments must separate discovery URL from expected issuer, register the
canonical Atlas callback, review historical source bindings, and classify
legacy memberships before exact reconciliation.

Sessions and exact grants now have finite defaults; admin password access is a
separate disabled-by-default break-glass policy. Follow [Migrate and revoke
authentication state](../operating-atlas/authentication-migration.md) for the
forward, rollback, source, and grant boundaries.

## Pre-release behavior changes

These changes landed before the first tagged release. Review them if you ran
Atlas from an earlier checkout.

- **Migration history was regenerated.** The `catalog`, `ingestion`, `apis`,
  and `database-schema` migrations restart at `0001_initial`, and an entity's
  repository claim is now stored by Ingestion instead of on the core entity
  row. A database created from an earlier checkout cannot be migrated in place;
  recreate it (or restore from a backup taken on the same build). In return, a
  distribution that does not select Ingestion now migrates and starts, and the
  scheduler (`runapscheduler`) is part of Core and runs jobs for any selected
  plugin. See [Data safety](../operating-atlas/data-safety.md).
- **MCP writes reject unknown fields.** `create_entity` and `update_entity`
  now fail with a 400 when `spec` or `metadata` contains a key the kind does
  not accept, instead of ignoring it and reporting success. This includes
  `spec.relationships`, which was accepted and silently dropped; use
  `create_relationship` instead. A client or script that sent extra or
  misspelled keys must remove or correct them; `describe_kinds` lists the
  accepted fields. Ingestion and the REST API are unchanged. See [Strict
  validation](../features/mcp.md#strict-validation).
- **API specification URLs are fetched safely.** An API's `specUrl` now
  resolves only over HTTPS and only to publicly routable addresses; embedded
  credentials, fragments, redirects to private addresses, and responses over
  20 MiB are rejected. A `specUrl` that resolved before can now fail as
  `specResolveFailed`, and the API keeps its last successful specification.
  Add an intentionally internal host to `ATLAS_APIS_SPEC_URL_ALLOWLIST`; see
  [Allow an internal spec_url
  host](../configuration/environment-variables.md#allow-an-internal-spec_url-host).
- **Ingestion paths are confined to the repository.** `Include` `spec.paths`
  entries and `databaseSchema.sourceSqlPath` that are absolute, contain `..`,
  contain control characters, or reach outside the checkout through a symlink
  are rejected and recorded as an `IngestionIssue`. Fetched files, YAML
  nesting, `Include` depth, and included-file counts are bounded; see [Fetch
  and parse limits](../features/ingestion.md#fetch-and-parse-limits).
- **Production settings fail closed.** With `DJANGO_ENV=production`, Atlas
  refuses to start with a missing, example, or shorter-than-50-character
  `DJANGO_SECRET_KEY`, and the production Compose file requires an explicit
  `POSTGRES_PASSWORD`. `DJANGO_SECURE_SSL_REDIRECT` defaults to `true` in
  production Compose. Public password recovery is disabled when no real mail
  backend is configured.
- **Containers run as a non-root user.** The backend, initializer, and ingestor
  run as `appuser` (UID/GID `1000`). See [Containers run as a non-root
  user](../deployment/production.md#containers-run-as-a-non-root-user).
- **Free-text fields and lists have limits.** Titles, descriptions,
  documentation, labels, tags, links, inline specifications, SQL sources, and
  Flow steps are bounded; see [Create or edit catalog
  entities](../using-atlas/create-edit-entities.md#the-server-rejects-a-field-as-too-long-or-too-large).
- **`OIDC_ISSUER` is deprecated.** It was always a discovery-document URL. Use
  `OIDC_DISCOVERY_URL` and set `OIDC_EXPECTED_ISSUER` explicitly.
