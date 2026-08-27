// Derives a Flow step's visual node kind from its data.
//
// Entity-backed steps never carry an explicit type: their kind is parsed
// from `entity_ref`'s `kind:name` prefix, the same six kinds `RefSelect.tsx`'s
// `TARGET_REF_KINDS` already supports. A step's `query_ref`/`event_ref`
// is checked first — its
// mere presence selects the Call/Event kind, mirroring how `external_label`
// alone already selects `external`, and mutually exclusive with `entity_ref`
// (enforced server-side). `flow_ref`/`link_url` are checked next, ahead of the `external`/`step`
// fallbacks for the same reason — mere presence selects the kind, mutually
// exclusive with every other ref field server-side. Non-entity,
// non-Call/Event, non-Flow/Link steps split into `external` (an
// out-of-catalog reference, `external_label` set) and the `step` fallback (a
// plain step, optionally colored via `label_theme`).

import { ArrowsRotateRight, BranchesRight, Book, Bucket, Code, Compass, Cube, Database, Envelope, Flag, GraphNode, Globe, Layers, Link, Magnifier, PlugConnection, Person, Persons, Server, Thunderbolt } from '@gravity-ui/icons'
import type { IconData } from '@gravity-ui/uikit'
import type { FlowStep } from './flowLayout'
import { gravityIconComponent } from './gravityIcons'

export type FlowNodeKind = 'actor' | 'team' | 'component' | 'data' | 'api' | 'system' | 'external' | 'step' | 'call' | 'event' | 'flow' | 'link'

const ENTITY_REF_KIND_TO_NODE_KIND: Record<string, FlowNodeKind> = {
  user: 'actor',
  group: 'team',
  component: 'component',
  resource: 'data',
  api: 'api',
  system: 'system',
}

/** Returns the node kind to render a step as (`query_ref`/`event_ref`, `entity_ref`'s kind prefix, `flow_ref`/`link_url`, or `external`/`step`). */
export function flowNodeKindOf(step: FlowStep): FlowNodeKind {
  if (step.query_ref) return 'call'
  if (step.event_ref) return 'event'
  const entityRef = step.entity_ref
  if (entityRef) {
    const prefix = entityRef.slice(0, entityRef.indexOf(':'))
    const kind = ENTITY_REF_KIND_TO_NODE_KIND[prefix]
    if (kind) return kind
  }
  if (step.flow_ref) return 'flow'
  if (step.link_url) return 'link'
  if (step.external_label) return 'external'
  return 'step'
}

/** Display label for each node kind, shared by the node components and the "Add Step" type picker. */
export const FLOW_NODE_KIND_LABELS: Record<FlowNodeKind, string> = {
  actor: 'Actor',
  team: 'Team',
  component: 'Component',
  data: 'Data',
  api: 'API',
  system: 'System',
  external: 'External',
  step: 'Step',
  call: 'API Call',
  event: 'Event',
  flow: 'Flow',
  link: 'Link',
}

/** Per-kind default icon, shared by the node cards (`FlowNodes.tsx`) and the "Add Step" type picker (`FlowStepModal.tsx`) so both draw from one source. Step's entry is also its fallback icon (`stepIcon` below) when no per-instance icon is chosen. */
export const FLOW_NODE_KIND_ICONS: Record<FlowNodeKind, IconData> = {
  actor: Person,
  team: Persons,
  component: Cube,
  data: Database,
  api: PlugConnection,
  system: Layers,
  external: Compass,
  step: Flag,
  call: Magnifier,
  // `@gravity-ui/icons` has no `Bolt` — `Thunderbolt` is its closest match
  // (the Event kind's "Bolt icon").
  event: Thunderbolt,
  // Reuses the exact icon the "Flows" sidebar nav item already uses
  // (`navItems.ts`), for pre-existing user recognition.
  flow: BranchesRight,
  // Plain chain glyph, not `CircleLink` — every other kind's chip icon here
  // is an unframed flat glyph, and `CircleLink`'s circular framing would be
  // the only one breaking that consistency; `Link`'s shape is also
  // unambiguous against the read-only navigate button's own
  // `ArrowUpRightFromSquare` icon on the same card.
  link: Link,
}

/**
 * Resolves the icon to render for a Step: its own `icon` (a `@gravity-ui/icons`
 * component name, looked up via `gravityIconComponent`) wins,
 * falling back to Step's fixed default icon (`FLOW_NODE_KIND_ICONS.step`)
 * when no icon is chosen or a stored name no longer resolves to a known icon
 */
export function stepIcon(step: { icon?: string }): IconData {
  return (step.icon && gravityIconComponent(step.icon)) || FLOW_NODE_KIND_ICONS.step
}

/**
 * Resolves the type chip label to render for a Step: its own `type_label`
 * (trimmed, non-blank) wins, falling back to Step's fixed default label
 * (`FLOW_NODE_KIND_LABELS.step`, "Step") when unset or blank/whitespace-only
 */
export function stepTypeLabel(step: { type_label?: string }): string {
  const trimmed = step.type_label?.trim()
  return trimmed || FLOW_NODE_KIND_LABELS.step
}

// Component/API/Data real-subtype icons —
// duplicated from `core/frontend/src/lib/icons.ts`'s private
// `COMPONENT_TYPE_ICONS`/`API_TYPE_ICONS`/`RESOURCE_TYPE_ICONS` tables (only
// their `componentTypeIcon`/`apiTypeIcon`/`resourceTypeIcon` accessor
// functions are exported there), mirroring `flowNodePalette.ts`'s
// `METHOD_COLORS`/`DIRECTION_COLORS` duplication: a Component/API/Data Flow
// node needs the real per-subtype icon (service/website/library/worker,
// openapi/grpc/asyncapi/graphql, database/cache/bucket/queue/cluster) instead
// of one fixed icon shared by every subtype.
const COMPONENT_TYPE_ICONS: Record<string, IconData> = {
  service: Cube,
  website: Globe,
  library: Book,
  worker: ArrowsRotateRight,
}

const API_TYPE_ICONS: Record<string, IconData> = {
  openapi: Code,
  grpc: PlugConnection,
  asyncapi: Envelope,
  graphql: GraphNode,
}

const RESOURCE_TYPE_ICONS: Record<string, IconData> = {
  database: Database,
  cache: Thunderbolt,
  bucket: Bucket,
  queue: Envelope,
  cluster: Server,
}

/** Icon for a Component's real `type` — falls back to Component's generic icon when `type` is undefined (subtype unresolved) or unrecognized. */
export function componentTypeIcon(type: string | undefined): IconData {
  return (type && COMPONENT_TYPE_ICONS[type]) || FLOW_NODE_KIND_ICONS.component
}

/** Icon for an API's real `type` — falls back to API's generic icon when `type` is undefined (subtype unresolved) or unrecognized. */
export function apiTypeIcon(type: string | undefined): IconData {
  return (type && API_TYPE_ICONS[type]) || FLOW_NODE_KIND_ICONS.api
}

/** Icon for a Data (Resource) entity's real `type` — falls back to Data's generic icon when `type` is undefined (subtype unresolved) or unrecognized. */
export function resourceTypeIcon(type: string | undefined): IconData {
  return (type && RESOURCE_TYPE_ICONS[type]) || FLOW_NODE_KIND_ICONS.data
}

/** Event node chip label for a snapshotted `direction` (`'send'`/`'receive'`) — title-cased ("Send"/"Receive"); falls back to `FLOW_NODE_KIND_LABELS.event` when unset or unrecognized. */
export function eventDirectionLabel(direction: string | undefined): string {
  if (direction === 'send' || direction === 'receive') return direction[0].toUpperCase() + direction.slice(1)
  return FLOW_NODE_KIND_LABELS.event
}

/**
 * Clarifying copy for Flow's `external` kind — distinguishes a step with no catalog record at all from the
 * catalog's own unrelated `External` tag (a cataloged entity, e.g. a
 * Component representing Stripe, marked third-party). Shared by the "Add
 * Step" picker's External tile tooltip and the rendered External node's
 * tooltip so the wording stays in sync; `flowNodeKindOf` never reads
 * `metadata.tags`, so no code path links the two meanings.
 */
export const EXTERNAL_KIND_HELP_TEXT = 'A step with no catalog record at all — not the same as a cataloged entity (e.g. a Component) tagged "External" to mark it as third-party.'
