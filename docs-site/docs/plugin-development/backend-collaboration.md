---
title: Backend collaboration
description: Publish and consume backend contracts without importing a sibling plugin's implementation.
audience:
  - plugin-author
page-type: guide
---

# Backend collaboration

Use a backend collaboration contract when one plugin needs another plugin's
behavior or needs to participate in an owner-controlled workflow. Do not import
a sibling plugin's models, ORM queries, views, or private modules. The owning
plugin keeps its data and business rules; consumers depend on a small published
contract instead.

## Audience, prerequisites, and outcome

This guide is for backend plugin authors who have chosen a [plugin
layout](plugin-layouts.md), understand the [extension decision guide](choose-an-extension.md),
and can run composition checks for their distribution. It describes a narrow,
versioned contract with a clear provider, consumer, availability behavior, and
descriptor dependency.

Choose a [kind capability](entity-kinds-and-facets.md#declaring-what-a-kind-provides)
when a consumer needs to know what an entity kind supports. Choose a backend
service contract when a consumer needs to call behavior at runtime; these are
different uses of the word “capability”.

## Choose the narrowest contract

| Need | Use | Current Atlas example |
| --- | --- | --- |
| Target compatible entity kinds semantically | Entity Kind `provides` capability | C4 targets `architecture.subject.v1`, not a list of kind ids. |
| Resolve an optional named runtime service | Backend capability registry | The registry and typed result exist; no built-in plugin currently publishes a general service capability. |
| Let multiple implementations register under an owner-defined key | Plugin-owned keyed extension point | Ingestion resolves connectors and parsers by id. |
| Let each interested plugin take part in one Core workflow | Core-owned registry or direct contract | Plugins register one purge-reference scanner; Core runs every scanner during Purge. |
| Call a small Core-owned operation | Published API wrapper | Core binds entity helper implementations into `atlas_plugin_api` during runtime setup. |

Do not create an extension point for a one-off lookup. Conversely, do not add a
direct import merely because a contract currently has one consumer: the
provider's models and implementation remain private.

## Register after Django setup

Static descriptor metadata is imported before Django starts. Runtime
registration happens only from `register_runtime()`, after `django.setup()`.
The selected, active descriptors run this hook; a disabled plugin skips it, so
it contributes no kinds, permissions, or extension implementations.

```python
from atlas_plugin_api import PluginDescriptor, register_purge_scanner

PLUGIN = PluginDescriptor(
    id='atlas.inventory',
    version='0.1.0',
    compatibility={'atlasCore': '>=0.1 <1'},
    django_apps=('atlas_plugin_inventory',),
    entry_point='atlas_plugin_inventory.plugin:PLUGIN',
    requires_plugins={'atlas.standard-catalog': '>=0.1 <1'},
)


def register_runtime() -> None:
    from .purge import scan_inventory_references

    register_purge_scanner(PLUGIN.id, scan_inventory_references)
```

Keep import-time modules declarative. Loading models, resolving a sibling
service, or mutating a registry during import makes static composition and
startup ordering unsafe. Duplicate registrations are errors: give every
registration a stable, plugin-owned id rather than overwriting another
provider.

## Capabilities and unavailable providers

An Entity Kind declares stable, versioned strings in `provides`; a consumer
uses `resolve_capability(kind_id, capability_id)` when it must distinguish an
absent kind provider from a present kind that simply lacks the capability. Its
result is one of `Ok(value)`, `Unavailable()`, or `Error(reason)`. Handle all
three cases explicitly:

```python
from atlas_plugin_api import Error, Ok, Unavailable, resolve_capability

result = resolve_capability(entity.kind, 'architecture.subject.v1')
match result:
    case Ok(True):
        render_diagram(entity)
    case Ok(False) | Unavailable():
        return  # This entity cannot participate, or its provider is inactive.
    case Error(reason):
        logger.warning('Capability lookup failed: %s', reason)
```

`Unavailable` is not permission denial and not a signal to reach into the
missing plugin's tables. Preserve a safe feature state, explain the absence if
the user needs an action, and let an operator restore a compatible plugin.
For the lifecycle effect on entities, see [Entity kinds & facets](entity-kinds-and-facets.md#unavailable-entities).

## Publish an extension point

An extension-point owner defines the identifier, contract, cardinality, keys,
and duplicate behavior. Put its registry with the owning plugin unless Core
needs to call every registered implementation. Use namespaced, versioned ids;
Ingestion's current keyed points are `atlas.ingestion.connectors.v1` and
`atlas.ingestion.parsers.v1`.

For a keyed point, one key maps to one implementation. The owner resolves the
implementation and treats a missing key as a normal unavailable integration.
Two implementations claiming the same key must fail, rather than leaving the
choice to import order. Ingestion's built-in Git connector and
`catalog-info.yaml` parser register in its runtime hook, and the pipeline
resolves them through the point instead of calling a hard-coded class.

Atlas does not currently ship a general public helper for creating arbitrary
extension points. Follow the source-backed Ingestion pattern only when your
plugin truly owns a multi-implementation contract, and document its identifier,
version, cardinality, allowed keys, owner, and error behavior. A general
registry without a selected consumer is not a supported integration surface.

## Direct contracts and failure isolation

Use a direct public wrapper for a narrow Core operation, or an owner-managed
registry for a workflow that must query all participants. For example, the
purge scanner is registered once per plugin and Core invokes every scanner in
the purge transaction. A scanner must self-filter entities it does not own,
return precise blocking references, and never silently delete another
plugin's data.

The Core entity helpers follow the same boundary from the other direction:
Core binds its implementations during `register_runtime()` and plugins call
the `atlas_plugin_api` wrappers. Calling such a wrapper before its provider
has registered is a startup error, not an invitation to import `server`.

Isolate failures at the contract boundary:

- return or surface an explicit unavailable result when an optional provider is absent;
- make duplicate ids and keys fail composition or startup with the competing owners;
- keep exceptions actionable and scoped to the participating plugin; and
- do not let a disabled plugin keep a runtime contribution or scheduled work active.

For a state-changing collaboration, add the provider's backend permission
check. Consumer-side UI gating only improves the user experience. See [Permissions](../concepts/permissions.md)
for the policy boundary.

## Declare dependency direction

Use `PluginDescriptor.requires_plugins` only when the consumer cannot operate
without the provider. It maps a provider plugin id to a version range, and
composition rejects a selected distribution that omits the required provider or
contains a dependency cycle. For example, plugins that require Standard
Catalog declare `{'atlas.standard-catalog': '>=0.1 <1'}`.

Do not declare an optional collaboration as required merely to simplify a
call. Check the capability or extension-point result and make the feature
unavailable when necessary. Dependencies point from consumer to provider;
never reverse that direction to force plugin load order.

## Verify and troubleshoot

1. Unit-test the provider contract, including each valid key or capability.
2. Test the consumer with the provider selected, absent, and disabled. Assert
   the expected unavailable or error state without importing provider internals.
3. Test duplicate registration and assert that the reported id/key and owners
   identify the correction.
4. Run the distribution composition preflight after changing a descriptor.

| Symptom | Likely cause | Safe correction |
| --- | --- | --- |
| `Unavailable()` result | Provider is not selected or is disabled | Render or return the documented unavailable state; select or enable a compatible provider if the feature is required. |
| Duplicate registration | Two active plugins claim one contract id or key | Give the new registration a plugin-owned id/key; never replace the existing registration. |
| Wrapper raises before serving requests | A published Core contract was called before runtime registration | Move the call out of import/setup code and use the public wrapper after Atlas starts. |
| Composition rejects a dependency | A required provider is absent or the graph cycles | Correct `requires_plugins` at the consumer and keep optional edges runtime-safe. |

Next, use [Plugin contract reference](reference.md) for exact Python symbols,
[Entity kinds & facets](entity-kinds-and-facets.md) for entity capabilities,
and [Assembling a distribution](../configuration/distributions.md) to validate
the selected plugin set.
