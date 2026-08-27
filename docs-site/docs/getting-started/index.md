---
title: Getting Started
description: Take a supported checkout to a running local Atlas instance and choose the next journey for your role.
audience:
  - evaluator
  - catalog-user
  - operator
page-type: landing
---

# Getting Started

This section takes you from a fresh checkout to a local Atlas instance you can
inspect. It covers setup, startup, health checks, and the first catalog steps
before you move on to daily use or operations.

## Who this section is for

Use this section if you are evaluating Atlas, joining a team that runs it, or
preparing a local environment. It explains:

- the prerequisites and environment values for a local run;
- the Compose topology for source-based development;
- how to check the running services and diagnose a failed start; and
- where to go after the first successful run.

## Start here

Begin with [Run Atlas locally](development.md). It is the source-mounted,
autoreloading path from a fresh checkout to a signed-in browser and a seeded
catalog entity with visible relationships.

## Recommended path

1. [Run Atlas locally](development.md): prepare the environment, start the
   source-based stack, apply migrations, load the demo, and inspect a System.
2. [Tour the demo catalog](catalog-tour.md): follow the seeded catalog from
   the home page through list, preview, detail, relations, and diagram views,
   then out to an API, a Flow, a Resource's schema, and the System Map.
3. [Environment variables](../configuration/environment-variables.md): check
   the meaning and safety of settings before changing the local defaults.
4. [Troubleshooting](../deployment/troubleshooting.md): use observable startup
   symptoms if the expected result is missing.
5. Continue with [Using Atlas](../using-atlas/index.md) to understand catalog
   data, or [Operating Atlas](../operating-atlas/index.md) for the
   production-like topology and routine operations.

## Section boundary

This journey covers a local first run, not production readiness, upgrades, or
recovery. Those procedures belong in [Operating
Atlas](../operating-atlas/index.md). The exact catalog model is maintained in
[Concepts and Architecture](../concepts/index.md).
