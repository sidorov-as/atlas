// Plain, pure contribution builders: each call returns an immutable
// data object at module-import time. None of them may have a side effect — no touching
// `window`, no mutating a registry — validation and activation both happen later, host-side.
import type {
  Contribution,
  EntityDetailTabContribution,
  FrontendPlugin,
  HomeWidgetContribution,
  NavItemContribution,
  RouteContribution,
  RouteRef,
} from './types'

export function route(input: Omit<RouteContribution, 'type'>): RouteContribution {
  return { type: 'route', ...input }
}

export function navItem(input: Omit<NavItemContribution, 'type'>): NavItemContribution {
  return { type: 'navItem', ...input }
}

export function entityDetailTab<TEntity>(
  input: Omit<EntityDetailTabContribution<TEntity>, 'type'>,
): EntityDetailTabContribution<TEntity> {
  return { type: 'entityDetailTab', ...input }
}

export function homeWidget(input: Omit<HomeWidgetContribution, 'type'>): HomeWidgetContribution {
  return { type: 'homeWidget', ...input }
}

/** A lazy reference resolved at validation time, not at declaration time. */
export function routeRef(id: string): RouteRef {
  return { __routeRef: true, id }
}

/**
 * Typed helper for gating a contribution on an Entity Kind's declared capability
 * (docs/plugin-architecture.md:186-205) rather than a hard-coded kind list. Checks the
 * `capabilities` list served on each entity's payload (populated from the backend's
 * `EntityKindRegistry`, entity-capabilities spec).
 */
export function entitySupports(capability: string): (entity: { capabilities?: readonly string[] }) => boolean {
  return (entity) => Array.isArray(entity.capabilities) && entity.capabilities.includes(capability)
}

export function defineFrontendPlugin(plugin: { id: string; contributions: readonly Contribution[] }): FrontendPlugin {
  return plugin
}
