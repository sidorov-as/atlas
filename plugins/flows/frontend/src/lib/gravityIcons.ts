// Reads `@gravity-ui/icons`' own `metadata.json` for the authoritative list
// of icon component names — the same names importable from
// `@gravity-ui/icons` (e.g. `Person`, `Cube`) and already used as
// `FLOW_NODE_KIND_ICONS`' fixed values (`flowNodeKind.ts`) — rather than
// hand-maintaining a duplicate list that would drift as the package updates
import iconMetadata from '@gravity-ui/icons/metadata.json'
import * as GravityIcons from '@gravity-ui/icons'
import type { IconData } from '@gravity-ui/uikit'

interface GravityIconMetadataEntry {
  name: string
  style: string
  svgName: string
  componentName: string
  keywords: string[]
  categories: string[]
}

const ICONS = (iconMetadata as { icons: GravityIconMetadataEntry[] }).icons

/** Every valid `@gravity-ui/icons` component name — Step's `icon` field validates against this set, and the icon picker searches over it. */
export const GRAVITY_ICON_NAMES: readonly string[] = ICONS.map((icon) => icon.componentName)

const GRAVITY_ICON_NAME_SET: ReadonlySet<string> = new Set(GRAVITY_ICON_NAMES)

/** True when `name` is a known `@gravity-ui/icons` component name. */
export function isGravityIconName(name: string): boolean {
  return GRAVITY_ICON_NAME_SET.has(name)
}

// `@gravity-ui/icons`' package root re-exports every icon as a named export
// keyed by its own `componentName` (verified against `metadata.json` above),
// so a namespace import doubles as the name -> component lookup —
// no separate hand-maintained map to keep in sync as the package
// adds icons.
const GRAVITY_ICON_COMPONENTS = GravityIcons as unknown as Record<string, IconData>

/** Resolves a `@gravity-ui/icons` component name to its icon component — `undefined` for a name that isn't a known icon, shared by the icon picker and node rendering (`flowNodeKind.ts`'s `stepIcon`) so both draw from one lookup. */
export function gravityIconComponent(name: string): IconData | undefined {
  return isGravityIconName(name) ? GRAVITY_ICON_COMPONENTS[name] : undefined
}

/** Caps the icon picker's result list — `@gravity-ui/icons` ships hundreds of icons, and a virtualized `Select` doesn't need every match rendered at once for a query to feel instant. */
const MAX_ICON_SEARCH_RESULTS = 60

/**
 * Name/keyword search over `@gravity-ui/icons`' `metadata.json` —
 * matches a query against each icon's component name, display name, and
 * keyword list, case-insensitively. An empty query returns the first
 * `MAX_ICON_SEARCH_RESULTS` icons (package order) rather than nothing, so the
 * picker isn't blank before a user types.
 */
export function searchGravityIcons(query: string, limit = MAX_ICON_SEARCH_RESULTS): string[] {
  const trimmed = query.trim().toLowerCase()
  if (!trimmed) return GRAVITY_ICON_NAMES.slice(0, limit)
  const matches = ICONS.filter((icon) =>
    icon.componentName.toLowerCase().includes(trimmed) ||
    icon.name.toLowerCase().includes(trimmed) ||
    icon.keywords.some((keyword) => keyword.toLowerCase().includes(trimmed)))
  return matches.slice(0, limit).map((icon) => icon.componentName)
}
