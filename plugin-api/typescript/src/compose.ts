// Build-time composition + validation (docs/plugin-architecture.md:332-363, ADR 0003/0020).
// Runs once over the full set of installed
// plugins, before the router or app shell is constructed; a validation failure throws
// instead of allowing a partially-built router to render.
import type {
  Contribution,
  EntityDetailTabContribution,
  ExtensionPointCardinality,
  FrontendPlugin,
  HomeWidgetContribution,
  NavItemContribution,
  RouteContribution,
} from './types'

/** The single in-tree contributor; reserved core paths may not be used by any other plugin. */
export const CORE_PLUGIN_ID = 'atlas.core'

/** Utility paths core owns outright; no plugin route may ever claim them. */
export const CORE_RESERVED_PATHS: readonly string[] = ['/', '/login', '/settings']

const EXTENSION_POINT_CARDINALITY: Record<Contribution['type'], ExtensionPointCardinality> = {
  route: 'collection',
  navItem: 'collection',
  entityDetailTab: 'collection',
  homeWidget: 'collection',
}

export class CompositionError extends Error {
  constructor(errors: readonly string[]) {
    super(`Frontend plugin composition failed:\n${errors.map((message) => `- ${message}`).join('\n')}`)
    this.name = 'CompositionError'
  }
}

export interface ResolvedNavItem extends NavItemContribution {
  readonly resolvedPath: string
}

export interface ComposedContributions {
  readonly routes: readonly RouteContribution[]
  readonly navItems: readonly ResolvedNavItem[]
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  readonly entityDetailTabs: readonly EntityDetailTabContribution<any>[]
  readonly homeWidgets: readonly HomeWidgetContribution[]
}

function assertCardinality(errors: string[], type: Contribution['type'], contributions: readonly { id: string }[]) {
  const cardinality = EXTENSION_POINT_CARDINALITY[type]
  if (cardinality === 'singleton' && contributions.length > 1) {
    errors.push(`Extension point "${type}" is singleton but received ${contributions.length} contributions: ${contributions.map((c) => c.id).join(', ')}`)
  }
}

/**
 * Validates and assembles every installed plugin's contributions. Throws `CompositionError`
 * (identifying every conflict at once, not just the first) rather than returning a partial result.
 */
export function composeFrontendPlugins(plugins: readonly FrontendPlugin[]): ComposedContributions {
  const errors: string[] = []
  const idOwners = new Map<string, string>()

  const routes: RouteContribution[] = []
  const navItems: NavItemContribution[] = []
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const entityDetailTabs: EntityDetailTabContribution<any>[] = []
  const homeWidgets: HomeWidgetContribution[] = []

  for (const plugin of plugins) {
    for (const contribution of plugin.contributions) {
      const existingOwner = idOwners.get(contribution.id)
      if (existingOwner) {
        errors.push(`Duplicate contribution id "${contribution.id}" declared by both "${existingOwner}" and "${plugin.id}"`)
      } else {
        idOwners.set(contribution.id, plugin.id)
      }

      switch (contribution.type) {
        case 'route':
          routes.push(contribution)
          if (plugin.id !== CORE_PLUGIN_ID && CORE_RESERVED_PATHS.includes(contribution.path)) {
            errors.push(`Route "${contribution.id}" (plugin "${plugin.id}") uses core-reserved path "${contribution.path}"`)
          }
          break
        case 'navItem':
          navItems.push(contribution)
          break
        case 'entityDetailTab':
          entityDetailTabs.push(contribution)
          break
        case 'homeWidget':
          homeWidgets.push(contribution)
          break
      }
    }
  }

  const pathOwners = new Map<string, string>()
  for (const routeContribution of routes) {
    const existingOwner = pathOwners.get(routeContribution.path)
    if (existingOwner && existingOwner !== routeContribution.id) {
      errors.push(`Route path "${routeContribution.path}" is declared by both "${existingOwner}" and "${routeContribution.id}"`)
    } else {
      pathOwners.set(routeContribution.path, routeContribution.id)
    }
  }

  const routeIds = new Set(routes.map((routeContribution) => routeContribution.id))
  const resolvedNavItems: ResolvedNavItem[] = []
  for (const navItemContribution of navItems) {
    if (!routeIds.has(navItemContribution.route.id)) {
      errors.push(`Nav item "${navItemContribution.id}" references unresolved route id "${navItemContribution.route.id}"`)
      continue
    }
    const resolvedPath = routes.find((routeContribution) => routeContribution.id === navItemContribution.route.id)!.path
    resolvedNavItems.push({ ...navItemContribution, resolvedPath })
  }

  assertCardinality(errors, 'route', routes)
  assertCardinality(errors, 'navItem', navItems)
  assertCardinality(errors, 'entityDetailTab', entityDetailTabs)
  assertCardinality(errors, 'homeWidget', homeWidgets)

  if (errors.length > 0) {
    throw new CompositionError(errors)
  }

  return { routes, navItems: resolvedNavItems, entityDetailTabs, homeWidgets }
}
