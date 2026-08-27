// Typed React Flow node components for Flow diagrams, following `TableNode.tsx`'s card structure. Every kind
// shares one card anatomy — neutral theme-aware fill, plain title/subtitle
// text, a small colored icon+label chip, and a bold (2px) colored border
// (`NodeCard`) — the only differences between kinds are where its
// icon/label/colors come from: fixed per kind for the six entity-backed
// kinds and External, derived from a snapshotted method/direction for
// API Call/Event, or author-chosen for Step.
import { memo, useState } from 'react'
import { Link as RouterLink } from 'react-router-dom'
import { Handle, Position, type NodeProps, type NodeTypes } from '@xyflow/react'
import { Button, Icon, Label, Text, Tooltip, type IconData } from '@gravity-ui/uikit'
import { ArrowUpRightFromSquare, Plus, Xmark } from '@gravity-ui/icons'
import { FLOW_NODE_HEIGHT, FLOW_NODE_WIDTH, type FlowNode, type FlowStepRefStatus } from '../lib/flowLayout'
import { apiTypeIcon, componentTypeIcon, EXTERNAL_KIND_HELP_TEXT, eventDirectionLabel, FLOW_NODE_KIND_ICONS, FLOW_NODE_KIND_LABELS, resourceTypeIcon, stepIcon, stepTypeLabel, type FlowNodeKind } from '../lib/flowNodeKind'
import { apiTypeColors, callMethodColors, componentTypeColors, eventDirectionColors, FLOW_NODE_PALETTE, resourceTypeColors, stepColors, type FlowNodeColors } from '../lib/flowNodePalette'
import { useEntitySubtype, useEntityRefDetails } from '../lib/entitySubtype'
import { useFlowRefDetails, type ResolvedFlowRef } from '../lib/flowRefDetails'
import { findFlowCatalogEntity, useFlowEntityCatalogOptional } from '../lib/flowEntityCatalog'
import { refName } from 'frontend/lib/types'
import { RefreshRefButton, StaleRefWarning, staleRefTooltip } from './FlowRefWarning'

/** One target + one source handle per node — Flow's default autolayout direction is left-right (`flowLayout.ts`). */
function FlowNodeHandles() {
  return (
    <>
      <Handle type="target" position={Position.Left} />
      <Handle type="source" position={Position.Right} />
    </>
  )
}

// Fixed (not min-) height: every card kind now renders the same box
// regardless of how many lines of text it actually has — a two-line Step
// (no summary) or the icon-only add-placeholder no longer end up visibly
// shorter than a three-line entity/External card. Each caller sets its own
// `justifyContent`: `NodeCard` top-anchors its chip/title so they land at the
// same Y-offset whether or not a subtitle is present
// — a block-centered layout would instead shift the chip/title down when the
// subtitle is missing, since centering redistributes free space above and
// below the shrunk content block. The icon-only add-placeholder still centers
// its single glyph, since it has no chip/title to anchor.
const CARD_STYLE_BASE = {
  boxSizing: 'border-box' as const,
  width: FLOW_NODE_WIDTH,
  height: FLOW_NODE_HEIGHT,
  padding: '8px 12px',
  borderRadius: 8,
  boxShadow: '0 1px 4px rgba(0, 0, 0, 0.12)',
  display: 'flex',
  flexDirection: 'column' as const,
  gap: 2,
  position: 'relative' as const,
}

/**
 * Always-visible delete affordance (editable canvas only — `data.onDelete` is
 * unset on the read-only detail-page canvas —
 * previously hover-only). A node click opens its edit modal, so "select the node, press Delete" collides with
 * that gesture; this gives deletion its own trigger. `stopPropagation` keeps
 * the click from also firing the node's `onClick` (which would reopen the
 * edit modal) or starting a drag.
 */
function NodeDeleteButton({ stepId, onDelete }: { stepId: string, onDelete: (stepId: string) => void }) {
  return (
    <Button
      size="xs"
      view="flat"
      // `nodrag` stops React Flow from treating this click as the start of a
      // node drag; the class also lets `onNodeClick` (FlowCanvasEditor.tsx)
      // recognize and ignore clicks that originated here — React Flow's own
      // node-click handling isn't reachable via React's synthetic
      // `stopPropagation` (see FlowCanvasEditor.tsx's `onNodeClick`).
      className="flow-graph__node-delete nodrag"
      aria-label="Remove step"
      onPointerDown={(event) => event.stopPropagation()}
      onClick={(event) => {
        event.stopPropagation()
        onDelete(stepId)
      }}
      style={{ position: 'absolute', top: 2, right: 2 }}
    >
      <Icon data={Xmark} size={12} />
    </Button>
  )
}

/**
 * Always-visible node-header add control (editable canvas only —
 * `data.onAddNext` is unset on the read-only detail-page canvas). Opens the same node-type picker "Add Step" uses,
 * connecting the new step as this node's outgoing transition (a new branch
 * if it already has one) once a type is chosen (`FlowCanvasEditor.tsx`'s
 * `addConnectedStep` wiring).
 */
function NodeAddNextButton({ stepId, onAddNext }: { stepId: string, onAddNext: (stepId: string) => void }) {
  return (
    <Button
      size="xs"
      view="flat"
      className="flow-graph__node-add-next nodrag"
      aria-label="Add next step"
      onPointerDown={(event) => event.stopPropagation()}
      onClick={(event) => {
        event.stopPropagation()
        onAddNext(stepId)
      }}
      style={{ position: 'absolute', top: 2, right: 22 }}
    >
      <Icon data={Plus} size={12} />
    </Button>
  )
}

/**
 * Read-only-canvas-only navigate control for a Flow or Link node
 * rendered only when
 * the caller passes `to` (an internal `/flows/:id` route) or `href` (an
 * external URL), which `FlowNodeComponent`/`LinkNodeComponent` only ever do
 * on the read-only detail-page canvas (`showNavigate` in `data`, set only by
 * `FlowGraph.tsx`) and, for Flow, only once the target is confirmed to
 * resolve. A real `react-router-dom` `Link` (internal) or plain `<a>`
 * (external), `target="_blank" rel="noopener noreferrer"`, so opening in a
 * new tab works via native middle-click/Cmd-or-Ctrl-click/right-click rather
 * than a `window.open()` a popup blocker could catch — `to`/`href` mirror
 * the established `<Button href=... target="_blank">` pattern already used
 * for external links elsewhere in the catalog (`system.tsx`'s link-out
 * buttons). `nodrag` mirrors the other overlay buttons; `nopan` is the one
 * that actually matters here — the read-only canvas has `nodesDraggable`
 * off, so a press-and-drag starting on a node otherwise falls through to
 * panning the viewport instead of registering as a click (the same `nodrag
 * nopan` pair `FlowEdges.tsx`'s interactive edge elements already use).
 */
function NodeNavigateButton({ to, href, label }: { to?: string, href?: string, label: string }) {
  const stopPointerDown = (event: { stopPropagation: () => void }) => event.stopPropagation()
  const stopClick = (event: { stopPropagation: () => void }) => event.stopPropagation()
  const button = to
    ? (
        <Button
          component={RouterLink}
          to={to}
          size="xs"
          view="flat"
          className="flow-graph__node-navigate nodrag nopan"
          aria-label={label}
          target="_blank"
          rel="noopener noreferrer"
          onPointerDown={stopPointerDown}
          onClick={stopClick}
          style={{ position: 'absolute', top: 2, right: 2 }}
        >
          <Icon data={ArrowUpRightFromSquare} size={12} />
        </Button>
      )
    : (
        <Button
          href={href}
          size="xs"
          view="flat"
          className="flow-graph__node-navigate nodrag nopan"
          aria-label={label}
          target="_blank"
          rel="noopener noreferrer"
          onPointerDown={stopPointerDown}
          onClick={stopClick}
          style={{ position: 'absolute', top: 2, right: 2 }}
        >
          <Icon data={ArrowUpRightFromSquare} size={12} />
        </Button>
      )
  return <Tooltip content={label} placement="top">{button}</Tooltip>
}

/**
 * Explains why an entity-backed node's (Actor/Team/Component/Data/API/System)
 * `entity_ref` is stale — same precedence as `staleRefTooltip` (`FlowRefWarning.tsx`),
 * distinct wording since an entity isn't "from the API". Never gains a drift
 * line — `entity_ref` is out of scope for stale-reference refresh.
 */
function staleEntityRefTooltip(refStatus: FlowStepRefStatus | undefined, label: string): string | null {
  if (!refStatus) return null
  if (refStatus.status === 'removed') return `This ${label} has been removed from the catalog.`
  if (refStatus.deprecated) return `This ${label} is deprecated.`
  return null
}

/**
 * Explains why a Flow node's `flow_ref` is stale — the referenced Flow no
 * longer exists. Unlike
 * `staleEntityRefTooltip`/`staleRefTooltip`, a Flow has no removed/deprecated
 * status of its own to distinguish; it either resolves or it doesn't, so this
 * only ever has the one message. `refStatus.name` present means the
 * server-resolved read confirms it exists — no warning. Absence of
 * `refStatus` alone is ambiguous (also true for a step added/re-pointed this
 * editing session, before the first save, which the server has never seen),
 * so this only warns once `clientDetails` (`useFlowRefDetails`'s same-session
 * fetch by id) has itself settled and found nothing — the actual "doesn't
 * exist" confirmation, not just "not yet resolved."
 *
 * Exported so `FlowStepModal.tsx`'s
 * in-modal warning (spec's "Stale Flow reference indicator" — "The same
 * warning icon and tooltip SHALL also render for the step being edited
 * inside the step-edit modal") reuses this exact function rather than a
 * second copy that could drift from the canvas card's.
 */
export function staleFlowRefTooltip(refStatus: FlowStepRefStatus | undefined, clientDetails: ResolvedFlowRef | null | undefined): string | null {
  if (refStatus?.name !== undefined) return null
  return clientDetails === null ? 'This Flow no longer exists.' : null
}

/**
 * Card shared by every node kind: a neutral,
 * theme-aware fill; a small colored chip (icon + kind label) via Gravity
 * UI's own theme-aware `Label`; plain (uncolored) title/subtitle text; and a
 * bold (2px) colored border. `icon`/`label`/`colors` are passed explicitly
 * rather than looked up from a `kind` prop here, since callers source them
 * differently: fixed per kind for Actor/Team/Component/Data/API/System/
 * External, derived from a snapshotted method/direction for API Call/Event
 * (`callMethodColors`/`eventDirectionColors`), and author-chosen for Step
 * (`stepColors`/`stepIcon`) — this card doesn't need to know which.
 *
 * The chip's wrapping `div`'s `alignSelf: 'flex-start'` (not on `Label`
 * directly — it isn't in `LabelProps`) keeps it its natural compact width
 * instead of stretching to the card's full width, the default for a flex
 * item in a column flex container.
 */
function NodeCard({ icon, label, colors, title, subtitle, stepId, onDelete, onAddNext, staleTooltip, chipTooltip, onRefresh, refreshLabel, navigateTo, navigateHref, navigateLabel }: { icon: IconData, label: string, colors: FlowNodeColors, title: string, subtitle?: string, stepId: string, onDelete?: (stepId: string) => void, onAddNext?: (stepId: string) => void, staleTooltip?: string | null, chipTooltip?: string, onRefresh?: () => void, refreshLabel?: string, navigateTo?: string, navigateHref?: string, navigateLabel?: string }) {
  const chip = (
    <Label theme={colors.theme} size="xs" icon={<Icon data={icon} size={12} />}>
      {label}
    </Label>
  )
  return (
    <div
      style={{
        ...CARD_STYLE_BASE,
        justifyContent: 'flex-start',
        border: `2px solid ${colors.border}`,
        background: 'var(--g-color-base-background)',
      }}
    >
      <FlowNodeHandles />
      {onDelete && <NodeDeleteButton stepId={stepId} onDelete={onDelete} />}
      {onAddNext && <NodeAddNextButton stepId={stepId} onAddNext={onAddNext} />}
      {/* Read-only-canvas-only (never coexists with onDelete/onAddNext above,
        which are editable-canvas-only — same top-right slot is fine). */}
      {navigateLabel && (navigateTo || navigateHref) && <NodeNavigateButton to={navigateTo} href={navigateHref} label={navigateLabel} />}
      {/* `aria-label` duplicates the tooltip's own text (same reasoning as
        `StaleRefWarning` above): conveys it to assistive tech, and makes it
        queryable in tests, without depending on `Tooltip`'s hover-triggered,
        portal-rendered content. Row (not just chip) so the stale-reference
        warning icon sits beside the chip instead of overlapping it. */}
      <div style={{ alignSelf: 'flex-start', display: 'flex', alignItems: 'center', gap: 4 }} aria-label={chipTooltip}>
        {chipTooltip ? <Tooltip content={chipTooltip} placement="top">{chip}</Tooltip> : chip}
        {staleTooltip && <StaleRefWarning tooltip={staleTooltip} />}
        {/* Passed for a Call/Event node with live drift (method+path/channel+
          direction for Event, or summary for either) — never for
          entity/Step/External. */}
        {onRefresh && <RefreshRefButton onClick={onRefresh} label={refreshLabel} />}
      </div>
      <Tooltip content={title} placement="top">
        <Text variant="body-2" ellipsis style={{ display: 'block' }}>
          {title}
        </Text>
      </Tooltip>
      {subtitle && (
        <Tooltip content={subtitle} placement="bottom">
          <Text color="secondary" variant="caption-2" ellipsis style={{ display: 'block' }}>
            {subtitle}
          </Text>
        </Tooltip>
      )}
    </div>
  )
}

/**
 * Actor/Team/Component/Data/API/System — type derived from `entity_ref`'s
 * kind prefix. Title/subtitle always come from the
 * referenced entity's *live* `title`/`description`, never from the step's
 * own (now-removed) `title`/`summary` — an entity-backed node's rendered
 * text always matches the catalog. The authoritative source is `refStatus`
 * (resolved server-side at read time); a step with no `refStatus` entry yet (just added,
 * or just re-pointed at a different reference, in the current edit session
 * — the server hasn't resolved it since nothing's been saved) falls back to
 * `useEntityRefDetails`'s client-side fetch of the same `title`/`description`,
 * so the card isn't blank while editing. Title falls further back to the
 * entity's raw name, then the step's id, for when the reference doesn't
 * resolve at all.
 * Component, API, and Data additionally resolve the referenced entity's real
 * subtype (`useEntitySubtype`) and use its actual icon/color instead of one
 * fixed identity for every subtype — falling back to a neutral default while
 * unresolved. For Data, the subtype is
 * the referenced Resource's `spec.type` (database/cache/bucket/queue/cluster).
 *
 * A just-added, not-yet-saved step (no `refStatus` yet) resolves its title
 * from the page-scoped `FlowEntityCatalogContext` (already-loaded, synchronous)
 * ahead of the `refName(entity_ref)` slug guess, so it settles on its real
 * catalog title immediately instead of flashing from a guess to
 * `clientDetails`'s own resolved title once that fetch completes. The lookup is `undefined` outside a provider (the
 * read-only Flow detail canvas never mounts one), in which case this falls
 * through to the pre-existing `clientDetails`/`refName` chain unchanged
 */
function EntityNodeComponent({ data, type }: NodeProps<FlowNode>) {
  const { step, onDelete, onAddNext, refStatus } = data
  const kind = type as Exclude<FlowNodeKind, 'step' | 'external' | 'call' | 'event'>
  const isSubtyped = kind === 'component' || kind === 'api' || kind === 'data'
  const subtype = useEntitySubtype(isSubtyped ? step.entity_ref : undefined)
  const icon =
    kind === 'component' ? componentTypeIcon(subtype) : kind === 'api' ? apiTypeIcon(subtype) : kind === 'data' ? resourceTypeIcon(subtype) : FLOW_NODE_KIND_ICONS[kind]
  const colors =
    kind === 'component' ? componentTypeColors(subtype) : kind === 'api' ? apiTypeColors(subtype) : kind === 'data' ? resourceTypeColors(subtype) : FLOW_NODE_PALETTE[kind]
  const hasLiveStatus = Boolean(refStatus?.title || refStatus?.description)
  const clientDetails = useEntityRefDetails(hasLiveStatus ? undefined : step.entity_ref)
  const entityCatalog = useFlowEntityCatalogOptional()
  const catalogEntity = findFlowCatalogEntity(entityCatalog?.itemsByKind, step.entity_ref)
  const title = refStatus?.title || clientDetails?.title || catalogEntity?.metadata.title || (step.entity_ref ? refName(step.entity_ref) : undefined) || step.id
  const subtitle = refStatus?.description || clientDetails?.description || undefined
  return (
    <NodeCard
      icon={icon}
      label={FLOW_NODE_KIND_LABELS[kind]}
      colors={colors}
      title={title}
      subtitle={subtitle}
      stepId={step.id}
      onDelete={onDelete}
      onAddNext={onAddNext}
      staleTooltip={staleEntityRefTooltip(refStatus, FLOW_NODE_KIND_LABELS[kind].toLowerCase())}
    />
  )
}
export const EntityFlowNode = memo(EntityNodeComponent)

/**
 * Flow: a step's `flow_ref`, referencing another Flow. Ref-backed like `EntityNodeComponent`
 * above: title/subtitle always come from the target Flow's live `name`/
 * `description`, never author-typed text. `refStatus` (server-resolved at
 * read time) is authoritative; `clientDetails` (`useFlowRefDetails`) is the
 * same-session fallback for a step with no `refStatus` entry yet — just
 * added, or just re-pointed at a different Flow, in the current edit
 * session — mirroring `EntityNodeComponent`'s `clientDetails` fallback for
 * `entity_ref`. The navigate control (`showNavigate`, read-only canvas only)
 * only renders once the target is confirmed to resolve, by either signal.
 */
function FlowNodeComponent({ data }: NodeProps<FlowNode>) {
  const { step, onDelete, onAddNext, refStatus, showNavigate } = data
  const resolvedByServer = refStatus?.name !== undefined
  const clientDetails = useFlowRefDetails(resolvedByServer ? undefined : step.flow_ref)
  const title = refStatus?.name || clientDetails?.name || step.id
  const subtitle = refStatus?.description || clientDetails?.description || undefined
  const resolves = resolvedByServer || Boolean(clientDetails)
  const canNavigate = showNavigate && resolves && step.flow_ref !== undefined && step.flow_ref !== null
  return (
    <NodeCard
      icon={FLOW_NODE_KIND_ICONS.flow}
      label={FLOW_NODE_KIND_LABELS.flow}
      colors={FLOW_NODE_PALETTE.flow}
      title={title}
      subtitle={subtitle}
      stepId={step.id}
      onDelete={onDelete}
      onAddNext={onAddNext}
      staleTooltip={staleFlowRefTooltip(refStatus, clientDetails)}
      // `?tab=flow` (read by `FlowDetailPage`'s initial-tab state) opens the
      // target Flow straight on its diagram, not its Overview tab — this
      // link always opens in a new tab (`target="_blank"`, `NodeNavigateButton`),
      // so react-router `state` can't carry the intent across browsing
      // contexts the way `FlowFormPage`'s `fromTab` does for same-tab nav; a
      // query param is the only channel that survives a fresh tab.
      navigateTo={canNavigate ? `/flows/${step.flow_ref}?tab=flow` : undefined}
      navigateLabel="Open this Flow"
    />
  )
}
// Named `FlowRefNode`, not `FlowNode` — `FlowNode` is already this file's
// import of the React Flow node type (`../lib/flowLayout`'s `type FlowNode`);
// distinct identifier avoids reader confusion even though TS itself would
// allow the clash (types and values live in separate namespaces).
export const FlowRefNode = memo(FlowNodeComponent)

/** Out-of-catalog reference: title + `external_label`, fixed External color. Chip carries an explanatory tooltip distinguishing this kind from the catalog's unrelated `External` tag. */
function ExternalNodeComponent({ data }: NodeProps<FlowNode>) {
  const { step, onDelete, onAddNext } = data
  return (
    <NodeCard
      icon={FLOW_NODE_KIND_ICONS.external}
      label={FLOW_NODE_KIND_LABELS.external}
      colors={FLOW_NODE_PALETTE.external}
      title={step.title || step.id}
      subtitle={step.external_label}
      stepId={step.id}
      onDelete={onDelete}
      onAddNext={onAddNext}
      chipTooltip={EXTERNAL_KIND_HELP_TEXT}
    />
  )
}
export const ExternalNode = memo(ExternalNodeComponent)

/**
 * Link: a step's `link_url`, an arbitrary external URL. Freeform like `ExternalNodeComponent` above:
 * title/summary are the author's own, optional text. Title falls back to the
 * URL itself when unset — never `step.id`, which is an opaque auto-generated
 * counter (`step-4`) carrying no information for a viewer — and the URL is
 * always shown as the subtitle regardless, mirroring how External's
 * `external_label` is always shown as its subtitle, so the card is never
 * informationally empty even with no author-typed title. The navigate
 * control (`showNavigate`, read-only canvas only) has nothing to resolve —
 * unlike Flow, an external URL either exists in the step or it doesn't.
 */
function LinkNodeComponent({ data }: NodeProps<FlowNode>) {
  const { step, onDelete, onAddNext, showNavigate } = data
  return (
    <NodeCard
      icon={FLOW_NODE_KIND_ICONS.link}
      label={FLOW_NODE_KIND_LABELS.link}
      colors={FLOW_NODE_PALETTE.link}
      title={step.title || step.link_url || step.id}
      subtitle={step.link_url ?? undefined}
      stepId={step.id}
      onDelete={onDelete}
      onAddNext={onAddNext}
      navigateHref={showNavigate && step.link_url ? step.link_url : undefined}
      navigateLabel="Open this link"
    />
  )
}
export const LinkNode = memo(LinkNodeComponent)

/**
 * API Call: a step's `query_ref`, colored by its snapshotted HTTP `method`,
 * chip labeled with the method itself (falling back to the generic label
 * when unresolved). Title/subtitle are always derived from the `query_ref`
 * snapshot itself — the method+path, and the picked Endpoint's own `summary`
 * (falling back to the owning API's raw name when that summary is blank) —
 * never author-typed text; a step always has a `query_ref` once its kind is Call
 * (enforced at save), so the step-id/no-subtitle fallbacks only matter for a
 * not-yet-picked in-progress step. No fetch: everything rendered here comes
 * from the step's own JSON, preserving the offline-canvas-render invariant
 * `query_ref`/`event_ref` snapshots exist for.
 */
function CallNodeComponent({ data }: NodeProps<FlowNode>) {
  const { step, onDelete, onAddNext, onRefresh, refStatus } = data
  const queryRef = step.query_ref
  return (
    <NodeCard
      icon={FLOW_NODE_KIND_ICONS.call}
      label={queryRef?.method || FLOW_NODE_KIND_LABELS.call}
      colors={callMethodColors(queryRef?.method ?? '')}
      title={queryRef ? `${queryRef.method} ${queryRef.path}` : step.id}
      subtitle={queryRef ? (queryRef.summary || refName(queryRef.api)) : undefined}
      stepId={step.id}
      onDelete={onDelete}
      onAddNext={onAddNext}
      staleTooltip={staleRefTooltip(refStatus, 'endpoint')}
      // Only when the picked Endpoint's own summary has drifted — a
      // query_ref's method/path cannot drift by construction, so summary is
      // the only thing this node ever has to refresh.
      onRefresh={refStatus?.live?.summary !== undefined && onRefresh ? () => onRefresh(step.id) : undefined}
      refreshLabel="Refresh from live endpoint"
    />
  )
}
export const CallNode = memo(CallNodeComponent)

/**
 * Event: a step's `event_ref`, colored by its snapshotted `direction`, chip
 * labeled with the title-cased direction (falling back to the generic label
 * when unresolved). Title/subtitle are always derived from the `event_ref`
 * snapshot itself — the channel+direction, and the picked Operation's own
 * `summary` (falling back to the owning API's raw name when that summary is
 * blank) — never author-typed text, mirroring `CallNodeComponent`. No fetch:
 * everything rendered here comes from the step's own JSON, preserving the
 * offline-canvas-render invariant `query_ref`/`event_ref` snapshots exist
 * for.
 */
function EventNodeComponent({ data }: NodeProps<FlowNode>) {
  const { step, onDelete, onAddNext, onRefresh, refStatus } = data
  const eventRef = step.event_ref
  return (
    <NodeCard
      icon={FLOW_NODE_KIND_ICONS.event}
      label={eventDirectionLabel(eventRef?.direction)}
      colors={eventDirectionColors(eventRef?.direction ?? '')}
      title={eventRef ? `${eventRef.channel} (${eventRef.direction})` : step.id}
      subtitle={eventRef ? (eventRef.summary || refName(eventRef.api)) : undefined}
      stepId={step.id}
      onDelete={onDelete}
      onAddNext={onAddNext}
      staleTooltip={staleRefTooltip(refStatus, 'operation')}
      // Only when there's a live direction/channel and/or summary to pull in
      // never for a removed/deprecated-only warning, and
      // `onRefresh` itself is unset on the read-only detail-page canvas.
      onRefresh={refStatus?.live && onRefresh ? () => onRefresh(step.id) : undefined}
    />
  )
}
export const EventNode = memo(EventNodeComponent)

/**
 * Plain step — same `NodeCard` anatomy as every other kind, the only difference being where its icon, label, and color
 * come from: `stepIcon` resolves the author's chosen `@gravity-ui/icons`
 * name, falling back to Step's default icon; `stepTypeLabel`
 * resolves the author's chosen `type_label`, falling back to "Step"
 * `stepColors` resolves
 * `step.color`, falling back to a migrated `label_theme` so an unmigrated
 * flow still renders correctly without requiring a re-save.
 */
function StepNodeComponent({ data }: NodeProps<FlowNode>) {
  const { step, onDelete, onAddNext } = data
  return (
    <NodeCard
      icon={stepIcon(step)}
      label={stepTypeLabel(step)}
      colors={stepColors(step)}
      title={step.title || step.id}
      subtitle={step.summary}
      stepId={step.id}
      onDelete={onDelete}
      onAddNext={onAddNext}
    />
  )
}
export const StepNode = memo(StepNodeComponent)

/**
 * Add-next placeholder — a dashed,
 * semi-transparent card with a centered "+", no title/kind/tooltip. Visually
 * inert: click handling for the whole card happens centrally in
 * `FlowCanvasEditor.tsx`'s `onNodeClick` (identical code path to the
 * node-header add control), keyed off this node's `type`, so
 * nothing here needs its own `onClick`. Never rendered on the read-only
 * detail-page canvas (that canvas's `nodes` never include one).
 *
 * Carries a target `Handle` (unlike the rest of this file's cards, which
 * only need it for real inbound transitions) so `FlowCanvasEditor.tsx` can
 * draw a dashed connector edge from the placeholder's own source step to it
 * — otherwise, once collision-avoidance (`resolveConnectedPosition`,
 * `flowLayout.ts`) has to push a placeholder away from its naive slot to
 * avoid overlapping an unrelated real node, there'd be nothing on screen
 * tying the ghost card back to the step it belongs to.
 */
function AddPlaceholderNodeComponent() {
  const [hovered, setHovered] = useState(false)
  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        ...CARD_STYLE_BASE,
        alignItems: 'center',
        justifyContent: 'center',
        border: `1px dashed ${hovered ? 'var(--g-color-line-focus)' : 'var(--g-color-line-generic)'}`,
        background: hovered ? 'var(--g-color-base-generic-hover)' : 'var(--g-color-base-generic)',
        opacity: hovered ? 1 : 0.6,
        cursor: 'pointer',
      }}
    >
      <Handle type="target" position={Position.Left} style={{ visibility: 'hidden' }} />
      <Icon data={Plus} size={16} />
    </div>
  )
}
export const AddPlaceholderNode = memo(AddPlaceholderNodeComponent)

/** Shared `nodeTypes` map, consumed by both the read-only detail-page canvas and the editable canvas. */
export const FLOW_NODE_TYPES: NodeTypes = {
  actor: EntityFlowNode,
  team: EntityFlowNode,
  component: EntityFlowNode,
  data: EntityFlowNode,
  api: EntityFlowNode,
  system: EntityFlowNode,
  external: ExternalNode,
  step: StepNode,
  call: CallNode,
  event: EventNode,
  flow: FlowRefNode,
  link: LinkNode,
  'add-placeholder': AddPlaceholderNode,
}
