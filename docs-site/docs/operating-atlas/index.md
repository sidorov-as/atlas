---
title: Operating Atlas
description: Run, configure, compose, verify, and troubleshoot the supported Atlas deployment topologies.
audience:
  - operator
page-type: landing
---

# Operating Atlas

This section explains how to configure and run an Atlas installation after the
first local evaluation. It covers the supported Compose topologies and the
build-time distribution choices that determine which plugins are included.

## Who this section is for

Use this section if you are responsible for configuration, deployment,
distribution composition, migrations, service health, logs, shutdown, or
recovery. It explains:

- which topology is appropriate for development or production-like use;
- which settings and secrets must be prepared before startup;
- how selected plugins become an immutable distribution; and
- how to verify or diagnose the running services safely.

## Start here

Read [Supported topologies](../deployment/index.md) first. It compares the
source-mounted development topology with the immutable production-like one and
defines the boundary of what Atlas currently supports.

## Recommended path

1. [Supported topologies](../deployment/index.md): choose the development or
   production-like Compose topology.
2. [Production-like topology](../deployment/production.md): complete the
   secrets, host/origin, database, composition, startup-order, and health
   preflight. Then run immutable images behind the same-origin gateway.
3. [Choose an authentication method](authentication.md): compare local, OIDC,
   Gitea, custom providers, and unsupported browser/API capabilities.
4. Follow the provider guide for [local](local-authentication.md),
   [OIDC](oidc-authentication.md), or [Gitea](gitea-authentication.md), then
   configure [Principal/Actor provisioning](identity-provisioning.md) and
   [Group reconciliation](group-reconciliation.md).
5. [Secure browser authentication](authentication-security.md): configure
   origins, outbound trust, sessions, recovery, secrets, and diagnostics.
6. [Migrate and revoke authentication state](authentication-migration.md):
   move existing deployments and operate exact links and grants.
7. [Read-only accounts](read-only-accounts.md): restrict an account's writes,
   audit the change, recover from operator lockout, and plan safe rollout or
   rollback.
8. [Environment variables](../configuration/environment-variables.md): review
   configuration ownership, required values, and secret handling.
9. [Assembling a distribution](../configuration/distributions.md): select and
   validate the Core and plugin artifacts included at build time.
10. [Fix composition errors](composition-errors.md) and [change plugin lifecycle](plugin-lifecycle.md):
   correct validation failures and make selection changes safely.
11. [Database changes and data safety](data-safety.md) and [upgrade](upgrade.md):
   apply migrations, establish the backup boundary, and deploy an upgrade.
12. [Operations](../deployment/operations.md): run migrations, inspect logs,
   stop services, and intentionally reset local data.
13. [Troubleshooting](../deployment/troubleshooting.md): diagnose failures from
    an observable symptom.

## Section boundary

Atlas documents Compose-based development and production-like topologies. It
does not support Kubernetes or provider integrations that have not been
implemented. Browser authentication does not add API bearer-token support. Use [Getting Started](../getting-started/index.md)
for a first local run and [Reference](../reference/index.md) for exact
configuration and contract lookup.
