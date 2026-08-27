// Shared "stale reference" warning + "refresh from live data" control
// (one shared implementation) — consumed by both `FlowNodes.tsx`'s canvas card and
// `FlowStepModal.tsx`'s in-modal warning, so there is exactly one
// implementation of each, not two independently-drifting copies.
import { Button, Icon, Tooltip } from '@gravity-ui/uikit'
import { ArrowRotateRight, TriangleExclamation } from '@gravity-ui/icons'
import { FLOW_NODE_SWATCHES } from '../lib/flowNodePalette'
import type { FlowStepRefStatus } from '../lib/flowLayout'

/**
 * Explains why an API Call/Event node's `query_ref`/`event_ref` is stale —
 * stacks every applicable condition rather than picking one
 * removed/deprecated copy (if
 * any), then the before/after direction/channel drift comparison (`event_ref`
 * only — an Endpoint's `method`/`path` is its own upsert identity and cannot
 * drift by construction), then the before/after summary drift (either kind) —
 * each line independent of the others, since e.g. an Operation's summary can
 * change without its direction/channel changing, or vice versa. `null` when
 * nothing is stale.
 */
export function staleRefTooltip(refStatus: FlowStepRefStatus | undefined, label: string): string | null {
  if (!refStatus) return null
  const lines: string[] = []
  if (refStatus.status === 'removed') lines.push(`This ${label} was removed from the API since this reference was captured.`)
  else if (refStatus.deprecated) lines.push(`This ${label} is deprecated.`)
  if (refStatus.live?.direction !== undefined && refStatus.live?.channel_address !== undefined) {
    lines.push(`Live ${label} is now ${refStatus.live.direction} ${refStatus.live.channel_address}.`)
  }
  if (refStatus.live?.summary !== undefined) lines.push(`Live ${label} summary is now "${refStatus.live.summary}".`)
  return lines.length > 0 ? lines.join(' ') : null
}

/**
 * Stale-reference warning icon — reuses the exact
 * visual precedent already in the catalog (`EndpointDetailPage.tsx`'s orange
 * `TriangleExclamation` + "Deprecated" `Label`), scaled down to an icon-only
 * affordance. Purely a rendering signal: never touches the step's stored
 * `query_ref`/`event_ref`/`entity_ref`.
 */
export function StaleRefWarning({ tooltip }: { tooltip: string }) {
  return (
    <Tooltip content={tooltip} placement="top">
      {/* `aria-label` duplicates the tooltip's own text so the warning is
        conveyed to assistive tech (and is queryable in tests) without
        depending on `Tooltip`'s hover-triggered, portal-rendered content. */}
      <div aria-label={tooltip} style={{ display: 'flex' }}>
        <Icon data={TriangleExclamation} size={14} style={{ color: FLOW_NODE_SWATCHES.warning.text }} />
      </div>
    </Tooltip>
  )
}

/**
 * Opt-in "pull live values into the form" action (also used for `query_ref`/Call now
 * that a `query_ref`'s `summary` can drift too) — the caller renders it
 * only next to an active drift warning (`refStatus.live` present), never for
 * `removed`/`deprecated` alone. Writes to in-memory form state only via
 * `onClick`; nothing is persisted until the author explicitly saves the step.
 *
 * `label` defaults to the original Event-node copy so existing call sites
 * are unaffected; pass `'Refresh from live endpoint'` for a Call node.
 *
 * `nodrag`/`stopPropagation` mirror `NodeDeleteButton`/`NodeAddNextButton`
 * (`FlowNodes.tsx`) so a click on the canvas card doesn't also start a React
 * Flow drag or reopen the modal without the refresh flag; harmless when this
 * renders inside `FlowStepModal`'s plain form instead.
 */
export function RefreshRefButton({ onClick, label = 'Refresh from live operation' }: { onClick: () => void, label?: string }) {
  return (
    <Tooltip content={label} placement="top">
      <Button
        size="xs"
        view="flat"
        className="nodrag"
        aria-label={label}
        onPointerDown={(event) => event.stopPropagation()}
        onClick={(event) => {
          event.stopPropagation()
          onClick()
        }}
      >
        <Icon data={ArrowRotateRight} size={12} />
      </Button>
    </Tooltip>
  )
}
