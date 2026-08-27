// Contract types for frontend plugin contributions (docs/plugin-architecture.md:266-380, ADR 0003/0005/0010/0011/0022).
// Internal 0.x contract package (ADR 0021) — published as the `@atlas/plugin-api`
// workspace package (`plugin-api/typescript`), not yet a stable public SDK.
import type { ComponentType, FunctionComponent, SVGProps } from 'react'

export type ExtensionPointCardinality = 'collection' | 'singleton' | 'keyed'

/** A lazy reference to a route id, resolved at composition time rather than at declaration time. */
export interface RouteRef {
  readonly __routeRef: true
  readonly id: string
}

export function isRouteRef(value: unknown): value is RouteRef {
  return typeof value === 'object' && value !== null && (value as { __routeRef?: unknown }).__routeRef === true
}

export interface RouteContribution {
  readonly type: 'route'
  readonly id: string
  readonly path: string
  readonly component: ComponentType
  /** Bypasses the session guard + nav shell layout core wraps every other route in (e.g. `/login`). Defaults to `false`. */
  readonly public?: boolean
  /**
   * Marks this route as a pure mutation destination (a create/edit form with no read-only
   * use) — core redirects a read-only session away from it before rendering
   * (a read-only session is
   * redirected away from a create or edit URL). Declared per route rather than inferred
   * from id/path so each plugin's own route list is the inventory, not a central guess.
   * Defaults to `false`.
   */
  readonly write?: boolean
}

export interface NavItemContribution {
  readonly type: 'navItem'
  readonly id: string
  readonly title: string
  /** Matches Gravity UI's icon component shape (`@gravity-ui/icons`'s exports, `AsideHeaderItem.icon`). */
  readonly icon?: FunctionComponent<SVGProps<SVGSVGElement>>
  readonly route: RouteRef
}

/**
 * `TEntity` is intentionally loose (defaults to `unknown`) since one global list of
 * `entityDetailTab` contributions spans every Entity Kind; `when` is what narrows a
 * contribution to the kind(s) it applies to, not the type parameter itself.
 */
export interface EntityDetailTabContribution<TEntity = unknown> {
  readonly type: 'entityDetailTab'
  readonly id: string
  readonly value: string
  readonly label: string
  readonly when: (entity: TEntity) => boolean
  readonly component: ComponentType<{ entity: TEntity }>
  /** Lets canvas-like content use the full page width instead of the shell's right rail. */
  readonly fullWidth?: boolean
}

export interface HomeWidgetContribution {
  readonly type: 'homeWidget'
  readonly id: string
  readonly component: ComponentType
}

export type Contribution =
  | RouteContribution
  | NavItemContribution
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  | EntityDetailTabContribution<any>
  | HomeWidgetContribution

export interface FrontendPlugin {
  readonly id: string
  readonly contributions: readonly Contribution[]
}
