---
title: Overview
description: Understand what Atlas is, how a distribution is shaped, and where to begin for each reader journey.
audience:
  - evaluator
  - catalog-user
  - operator
  - plugin-author
page-type: landing
---

# Overview

Atlas is an extensible software catalog that brings software ownership,
relationships, interfaces, architecture, resources, and operational context
together. This section gives new readers enough product and architecture
context to choose their next step.

## Who this section is for

Start here if you are evaluating Atlas or need a shared understanding of its
product scope before using, operating, or extending it. The pages in this path
explain:

- what runs in an Atlas installation;
- how Core and selected plugins become a distribution;
- which catalog concepts stay consistent across features; and
- where catalog users, operators, and plugin authors should continue.

## Start here

Read [System shape](../concepts/system-shape.md) first. It identifies the
backend, frontend, database, ingestion worker, distribution, and trust
boundaries without requiring knowledge of the repository layout.

## Recommended path

1. [System shape](../concepts/system-shape.md) describes the supported runtime
   and ownership boundaries.
2. [Architectural principles](../concepts/principles.md) explains the
   constraints behind build-time composition and plugin isolation.
3. [Entity model](../concepts/entity-model.md) explains what the catalog stores
   and how its kinds relate.
4. Choose a journey:
   [Getting Started](../getting-started/index.md) to run Atlas,
   [Using Atlas](../using-atlas/index.md) to work with catalog data,
   [Operating Atlas](../operating-atlas/index.md) to manage an installation, or
   [Plugin Development](../plugin-development/index.md) to extend a
   distribution.

## Section boundary

Overview explains the supported product shape. Setup commands, operating
procedures, and extension contracts live in the journey links above. Use
[Concepts and Architecture](../concepts/index.md) for the reusable domain model
in more depth.
