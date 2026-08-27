---
title: Concepts and Architecture
description: Learn the stable domain models and architectural boundaries behind Atlas workflows and extension contracts.
audience:
  - evaluator
  - catalog-user
  - operator
  - plugin-author
  - contributor
page-type: landing
---

# Concepts and Architecture

This section explains the models and constraints used across Atlas task
guides, feature guides, and reference material. Use it to understand why an
entity, permission, or plugin behaves as it does.

## Who this section is for

This section is for readers who need the terminology and models behind Atlas
workflows. It covers:

- how Atlas names and relates catalog entities;
- how entity provenance and lifecycle states affect allowed changes;
- how authentication, identity, ownership, and permissions connect; and
- which runtime and plugin boundaries Atlas preserves.

## Glossary

The [Domain glossary](glossary.md) defines Entity Kind, Facet, Contribution,
Capability, Extension Point, Distribution, and other terms used throughout the
site.

## Reading order

1. [Domain glossary](glossary.md): shared vocabulary.
2. [Entity model](entity-model.md): kinds, metadata, specs, and relationships.
3. [Entity references](entity-references.md): reference identity and resolution.
4. [Life of an entity](life-of-an-entity.md): provenance, claims, availability,
   removal, revival, and purge.
5. [Auth and identity](auth-and-identity.md), then
   [Permissions](permissions.md): how a signed-in principal connects to ownership
   and policy evaluation.
6. [System shape](system-shape.md), then [Architectural
   principles](principles.md): runtime composition, trust, and isolation boundaries.

## Section boundary

Concept pages explain models. For procedures, see [Using Atlas](../using-atlas/index.md),
[Operating Atlas](../operating-atlas/index.md), and [Plugin
Development](../plugin-development/index.md). [Reference](../reference/index.md)
lists exact fields, identifiers, and API contracts.
