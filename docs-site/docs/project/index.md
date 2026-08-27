---
title: Project
description: Find the contributor workflow, repository entry points, and the architectural expectations for changing Atlas.
audience:
  - contributor
page-type: landing
---

# Project

This section explains how to change Atlas. It covers the contributor workflow
and the architectural rules that code, documentation, tests, migrations, and
proposals must follow.

## Who this section is for

Use this section when you plan to submit or review an Atlas change. It explains:

- how a proposed change moves from an issue through review and merge;
- where backend and frontend development commands live;
- which architectural constraints a contribution must follow; and
- when to use product or plugin-author documentation instead of Core
  contribution guidance.

## Start here

Read [Contributing](../contributing/index.md) first for development entry points,
validation expectations, the proposal workflow, and licensing.

## Suggested reading order

1. [Contributing](../contributing/index.md): set up a development workflow and
   learn how changes are proposed and reviewed.
2. [System shape](../concepts/system-shape.md): identify the runtime and package
   ownership boundaries your change affects.
3. [Architectural principles](../concepts/principles.md): review composition,
   isolation, and dependency constraints before editing implementation code.
4. [Plugin Development](../plugin-development/index.md): use public extension
   contracts when your change belongs in a plugin rather than Core.
5. [Documentation authoring standards](https://github.com/sidorov-as/atlas/tree/main/docs-site/authoring):
   follow the page contracts and feature guide template, and use source-backed
   examples when changing the site.

## Repository and review workflow

Core lives in `core/`; selected product extensions live in `plugins/`;
`composer/` contains composition tooling; `distributions/` contains distribution
inputs; and `docs-site/` contains the canonical site. Check the component README
for local debug commands, then run the focused tests and validation closest to
your change.

Documentation changes must preserve navigation and internal links, satisfy the
page contract, validate examples, and build cleanly with `uv run zensical build
--clean` from `docs-site/`. Review the linked issue and its agreed approach
with the implementation. For unsupported behavior, submit a deliberate
follow-up instead of a placeholder.

## Section boundary

Project documentation covers work on the Atlas repository. It does not replace
[Getting Started](../getting-started/index.md) for a first run, [Operating
Atlas](../operating-atlas/index.md) for an installation, or [Using
Atlas](../using-atlas/index.md) for catalog tasks.
