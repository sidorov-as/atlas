// Theme-aware node palette for the Flow canvas. Every
// color here is one of Gravity UI's own semantic theme tokens — the same
// six-name vocabulary (`normal`/`info`/`success`/`warning`/`danger`/
// `utility`) Step's `label_theme` field already used — rather than fixed
// hex. `ThemeProvider` (`core/frontend/src/App.tsx`) already keeps these
// tokens coordinated for light and dark, so the palette gets dark-mode
// support for free instead of needing its own light/dark hex table.
//
// This is no longer sourced from (or coupled to)
// `plugins/c4/backend/atlas_plugin_c4/c4.py`'s `_ATLAS_PLANTUML_TAGS` — that
// deliberate duplication this file used to document is over. Flow's canvas
// (React Flow, live theme switching) and the `c4` plugin's PlantUML SVGs
// (server-rendered, no theme awareness) are different rendering pipelines
// and are expected to diverge visually from here on.

import type { FlowNodeKind } from './flowNodeKind'

/** Gravity UI `Label` theme name. `FlowNodeTheme` below is the subset this palette actually assigns to a kind or offers as a Step swatch; `clear` shows up only in `METHOD_COLORS` (OPTIONS has no real identity color of its own). */
export type GravityLabelTheme = 'normal' | 'info' | 'success' | 'warning' | 'danger' | 'utility' | 'clear'

/** The six-name vocabulary shared with `flowStepSchema.ts`'s (deprecated) `label_theme` field — also this palette's Step-swatch keys and the `label_theme` → `color` migration table's target. */
export type FlowNodeTheme = Exclude<GravityLabelTheme, 'clear'>

export interface FlowNodeColors {
  /** The underlying Gravity theme name — feeds a node's small identity chip (`<Label theme={theme}>`). */
  theme: GravityLabelTheme
  /** A node's 2px card border — the `--g-color-line-*` token matching `theme`. */
  border: string
  /** A node's card fill. Entity-backed kinds/External get `theme`'s tinted `-light` token; API Call/Event stay plain (matching their pre-existing white fill) since a tinted fill would make e.g. a GET API Call card indistinguishable from an API card. */
  fill: string
  /** A node's title/subtitle text color — `theme`'s `-heavy` text token. */
  text: string
}

const BORDER_TOKEN_BY_THEME: Record<GravityLabelTheme, string> = {
  normal: 'var(--g-color-line-misc)',
  info: 'var(--g-color-line-info)',
  success: 'var(--g-color-line-positive)',
  warning: 'var(--g-color-line-warning)',
  danger: 'var(--g-color-line-danger)',
  utility: 'var(--g-color-line-utility)',
  clear: 'var(--g-color-line-generic)',
}

const FILL_TOKEN_BY_THEME: Record<GravityLabelTheme, string> = {
  normal: 'var(--g-color-base-misc-light)',
  info: 'var(--g-color-base-info-light)',
  success: 'var(--g-color-base-positive-light)',
  warning: 'var(--g-color-base-warning-light)',
  danger: 'var(--g-color-base-danger-light)',
  utility: 'var(--g-color-base-utility-light)',
  clear: 'var(--g-color-base-background)',
}

const TEXT_TOKEN_BY_THEME: Record<GravityLabelTheme, string> = {
  normal: 'var(--g-color-text-misc-heavy)',
  info: 'var(--g-color-text-info-heavy)',
  success: 'var(--g-color-text-positive-heavy)',
  warning: 'var(--g-color-text-warning-heavy)',
  danger: 'var(--g-color-text-danger-heavy)',
  utility: 'var(--g-color-text-utility-heavy)',
  clear: 'var(--g-color-text-complementary)',
}

/** A fixed-kind identity color: tinted fill, per `theme` (unlike `callOrEventSwatch` below). */
function fixedKindSwatch(theme: GravityLabelTheme): FlowNodeColors {
  return { theme, border: BORDER_TOKEN_BY_THEME[theme], fill: FILL_TOKEN_BY_THEME[theme], text: TEXT_TOKEN_BY_THEME[theme] }
}

/** An API Call/Event color: same border/text as `fixedKindSwatch`, but a plain (theme-aware, not tinted) fill — preserves the pre-existing white-fill/bold-border "outlined" look that keeps an API Call/Event card from reading as a same-colored twin of an entity-backed card. */
function callOrEventSwatch(theme: GravityLabelTheme): FlowNodeColors {
  return { theme, border: BORDER_TOKEN_BY_THEME[theme], fill: 'var(--g-color-base-background)', text: TEXT_TOKEN_BY_THEME[theme] }
}

/** Kind-independent swatch set: every color a fixed kind can use, keyed by the same theme name Step's (deprecated) `label_theme` and future `color` field store. This is Step's color-picker option set, not a separate ad-hoc palette. */
export const FLOW_NODE_SWATCHES: Record<FlowNodeTheme, FlowNodeColors> = {
  normal: fixedKindSwatch('normal'),
  info: fixedKindSwatch('info'),
  success: fixedKindSwatch('success'),
  warning: fixedKindSwatch('warning'),
  danger: fixedKindSwatch('danger'),
  utility: fixedKindSwatch('utility'),
}

/** Default swatch for a Step with no explicitly chosen color — matches `StepNodeComponent`'s existing `label_theme ?? 'normal'` fallback. */
export const DEFAULT_STEP_THEME: FlowNodeTheme = 'normal'

/**
 * `label_theme` → `color` migration table. Identity by name: the deprecated `label_theme` field and the new
 * `color` field share the same six-name vocabulary (`FlowNodeTheme`), so a
 * legacy value maps straight onto the swatch of the same name — this table
 * exists as its own named export (rather than being inlined as `?? label_theme`
 * at call sites) so the migration is a documented, single-source-of-truth step
 * rather than an implicit assumption repeated wherever a step's color is read.
 */
export const LABEL_THEME_TO_COLOR: Record<FlowNodeTheme, FlowNodeTheme> = {
  normal: 'normal',
  info: 'info',
  success: 'success',
  warning: 'warning',
  danger: 'danger',
  utility: 'utility',
}

/**
 * Resolves the effective palette swatch for a Step: its own `color` wins,
 * falling back to a migrated `label_theme` (unmigrated flows render correctly
 * with no author action required),
 * then `DEFAULT_STEP_THEME` for a Step with neither set.
 */
export function stepColors(step: { color?: FlowNodeTheme; label_theme?: FlowNodeTheme }): FlowNodeColors {
  const theme = step.color ?? (step.label_theme ? LABEL_THEME_TO_COLOR[step.label_theme] : undefined) ?? DEFAULT_STEP_THEME
  return FLOW_NODE_SWATCHES[theme]
}

/** One fixed identity color per entity-backed kind and External, drawn from `FLOW_NODE_SWATCHES`. Actor/Team share a color, same as the palette this replaces. Component is `info` (not `success`) since no real Component ever renders `success` on canvas — its actual color is always subtype-derived (`componentTypeColors`); System is `success` (not `info`, shared with API) since System has no subtype system of its own and so is the only kind that both picks up this color and actually renders it. Flow and Link are `danger` and `warning` respectively — `danger` was the only swatch no fixed kind used yet; `warning` is reused from Actor/Team (already-established precedent that a shared swatch is fine) since Flow/Link only need to differ from *each other* and from their eventual picker-grid neighbors, not from every other kind globally. */
export const FLOW_NODE_PALETTE: Record<Exclude<FlowNodeKind, 'step' | 'call' | 'event'>, FlowNodeColors> = {
  actor: FLOW_NODE_SWATCHES.warning,
  team: FLOW_NODE_SWATCHES.warning,
  component: FLOW_NODE_SWATCHES.info,
  data: FLOW_NODE_SWATCHES.utility,
  api: FLOW_NODE_SWATCHES.info,
  system: FLOW_NODE_SWATCHES.success,
  external: FLOW_NODE_SWATCHES.normal,
  flow: FLOW_NODE_SWATCHES.danger,
  link: FLOW_NODE_SWATCHES.warning,
}

// API Call/Event node colors (re-expressed as theme-aware tokens) —
// a theme-name equivalent of `atlas_plugin_apis`'s
// `plugins/apis/frontend/src/lib/badges.ts` `METHOD_THEME`/`DIRECTION_THEME`,
// duplicated here rather than imported since `@atlas/plugin-flows` cannot
// depend on `@atlas/plugin-apis` (`importBoundary.test.ts`).

/** HTTP method -> API Call node colors, mirroring `badges.ts`'s `METHOD_THEME` theme assignment. */
export const METHOD_COLORS: Record<string, FlowNodeColors> = {
  GET: callOrEventSwatch('info'),
  POST: callOrEventSwatch('success'),
  PUT: callOrEventSwatch('warning'),
  PATCH: callOrEventSwatch('utility'),
  DELETE: callOrEventSwatch('danger'),
  HEAD: callOrEventSwatch('normal'),
  OPTIONS: callOrEventSwatch('clear'),
}
const DEFAULT_METHOD_COLORS = METHOD_COLORS.HEAD

/** API Call node colors for a snapshotted `method` — falls back to a neutral color for an unrecognized value. */
export function callMethodColors(method: string): FlowNodeColors {
  return METHOD_COLORS[method] ?? DEFAULT_METHOD_COLORS
}

/** `Operation.direction` -> Event node colors. `receive` mirrors `badges.ts`'s `DIRECTION_THEME`
 * (info); `send` deliberately breaks from it (success/green there) and instead reuses Team's
 * warning theme, so a Send event doesn't read as a same-color twin of the Component card. */
export const DIRECTION_COLORS: Record<string, FlowNodeColors> = {
  send: callOrEventSwatch('warning'), // matches Team/Actor
  receive: callOrEventSwatch('info'), // matches API/System
}
const DEFAULT_DIRECTION_COLORS = DIRECTION_COLORS.receive

/** Event node colors for a snapshotted `direction` — falls back to a neutral color for an unrecognized value. */
export function eventDirectionColors(direction: string): FlowNodeColors {
  return DIRECTION_COLORS[direction] ?? DEFAULT_DIRECTION_COLORS
}

/** Neutral fallback color — a Component/API node whose real subtype hasn't resolved, and the "Add Step" tile default for a kind with no fixed color of its own. */
export const NEUTRAL_COLORS: FlowNodeColors = { theme: 'clear', fill: 'var(--g-color-base-background)', text: 'var(--g-color-text-primary)', border: 'var(--g-color-line-generic)' }

// Component/API real-subtype colors — a
// theme-name duplicate of `core/frontend/src/lib/badges.ts`'s
// `COMPONENT_TYPE_THEME`/`API_TYPE_THEME`, mirroring the
// `METHOD_COLORS`/`DIRECTION_COLORS` duplication above: a Component/API Flow
// node needs the exact per-subtype identity color the catalog itself uses
// (service/website/library/worker, openapi/grpc/asyncapi/graphql), not
// `FLOW_NODE_PALETTE`'s single generic color shared by every subtype.

/** `ComponentType` -> Component node colors, mirroring `badges.ts`'s `COMPONENT_TYPE_THEME`. */
export const COMPONENT_TYPE_COLORS: Record<string, FlowNodeColors> = {
  service: fixedKindSwatch('info'),
  website: fixedKindSwatch('utility'),
  library: fixedKindSwatch('normal'),
  worker: fixedKindSwatch('clear'),
}

/** Component node colors for a resolved `type` — falls back to `NEUTRAL_COLORS` when `type` is undefined (subtype unresolved) or unrecognized. */
export function componentTypeColors(type: string | undefined): FlowNodeColors {
  return (type && COMPONENT_TYPE_COLORS[type]) || NEUTRAL_COLORS
}

/** `ApiType` -> API node colors, mirroring `badges.ts`'s `API_TYPE_THEME`. */
export const API_TYPE_COLORS: Record<string, FlowNodeColors> = {
  openapi: fixedKindSwatch('info'),
  grpc: fixedKindSwatch('utility'),
  asyncapi: fixedKindSwatch('normal'),
  graphql: fixedKindSwatch('clear'),
}

/** API node colors for a resolved `type` — falls back to `NEUTRAL_COLORS` when `type` is undefined (subtype unresolved) or unrecognized. */
export function apiTypeColors(type: string | undefined): FlowNodeColors {
  return (type && API_TYPE_COLORS[type]) || NEUTRAL_COLORS
}

/** `ResourceType` -> Data node colors, mirroring `badges.ts`'s `RESOURCE_TYPE_THEME`. */
export const RESOURCE_TYPE_COLORS: Record<string, FlowNodeColors> = {
  database: fixedKindSwatch('success'),
  cache: fixedKindSwatch('utility'),
  bucket: fixedKindSwatch('normal'),
  queue: fixedKindSwatch('clear'),
  cluster: fixedKindSwatch('danger'),
}

/** Data node colors for a resolved `type` — falls back to `NEUTRAL_COLORS` when `type` is undefined (subtype unresolved) or unrecognized. */
export function resourceTypeColors(type: string | undefined): FlowNodeColors {
  return (type && RESOURCE_TYPE_COLORS[type]) || NEUTRAL_COLORS
}
