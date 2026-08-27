// "Add Step" node-type picker and "edit existing node" modal for the Visual
// canvas editor. One dialog serves
// both flows: it opens on the tile picker when no type is known yet (a fresh
// Add Step, or after "Change type"), and on the type-specific field form
// once a kind is picked or (for edit) derived from the step being edited.
import { useEffect, useId, useRef, useState } from 'react'
import { Button, Dialog, Icon, Label, Select, Text, TextArea, TextInput, Tooltip } from '@gravity-ui/uikit'
import { Xmark } from '@gravity-ui/icons'
import type { RefKind } from 'frontend/components/RefSelect'
import { useDebouncedValue } from 'frontend/lib/useDebouncedValue'
import { refName } from 'frontend/lib/types'
import { flowsApi } from 'frontend/lib/entities'
import { nextFlowStepId, isHttpUrl } from './flowSteps'
import { LookupOptionRow, lookupSelectLoadingProps } from './LookupOptionRow'
import { useFlowEntityCatalog } from '../lib/flowEntityCatalog'
import { EXTERNAL_KIND_HELP_TEXT, flowNodeKindOf, FLOW_NODE_KIND_ICONS, FLOW_NODE_KIND_LABELS, type FlowNodeKind } from '../lib/flowNodeKind'
import { callMethodColors, DEFAULT_STEP_THEME, eventDirectionColors, FLOW_NODE_PALETTE, FLOW_NODE_SWATCHES, LABEL_THEME_TO_COLOR, NEUTRAL_COLORS, type FlowNodeColors, type FlowNodeTheme } from '../lib/flowNodePalette'
import { endpointsApi, operationsApi, type EndpointSearchResult, type OperationSearchResult } from '../lib/apiSearch'
import { GRAVITY_ICON_NAMES, gravityIconComponent, searchGravityIcons } from '../lib/gravityIcons'
import { isAtlasApisAvailable } from '../lib/pluginHealth'
import { RefreshRefButton, StaleRefWarning, staleRefTooltip } from './FlowRefWarning'
import { staleFlowRefTooltip } from './FlowNodes'
import { useFlowRefDetails } from '../lib/flowRefDetails'
import type { FlowStep, FlowStepEventRef, FlowStepLabelTheme, FlowStepQueryRef, FlowStepRefStatus } from '../lib/flowLayout'
import type { FlowEntity } from 'frontend/lib/types'

/** Step's color-picker swatch order — every key `FLOW_NODE_SWATCHES` defines, i.e. the same palette a fixed kind's border color is drawn from. */
const STEP_SWATCH_THEMES = Object.keys(FLOW_NODE_SWATCHES) as FlowNodeTheme[]

type EntityNodeKind = 'actor' | 'team' | 'component' | 'data' | 'api' | 'system'

const ENTITY_KIND_TO_REF_KIND: Record<EntityNodeKind, RefKind> = {
  actor: 'user',
  team: 'group',
  component: 'component',
  data: 'resource',
  api: 'api',
  system: 'system',
}

function isEntityNodeKind(kind: FlowNodeKind): kind is EntityNodeKind {
  return kind in ENTITY_KIND_TO_REF_KIND
}

// Order (2-column grid) chosen so no two adjacent tiles (same row or column)
// share a color, post the System/Component swap above — not a contract on the literal sequence,
// just one arrangement that satisfies the adjacency rule. Flow and Link
// are appended as a sixth row rather than
// interleaved: `danger` (Flow) and `warning` (Link) are each already distinct
// from the row above (event=warning/step=clear) and from each other, so the
// existing ten tiles' order/colors need no reshuffling to stay valid at
// twelve tiles, six full rows (the picker-grid
// requirement).
const KIND_TILES: { kind: FlowNodeKind; description: string }[] = [
  { kind: 'actor', description: 'A person or user' },
  { kind: 'system', description: 'A system' },
  { kind: 'api', description: 'An API' },
  { kind: 'data', description: 'A data store or resource' },
  { kind: 'external', description: 'An out-of-catalog reference' },
  { kind: 'component', description: 'A backend service or component' },
  { kind: 'call', description: 'A specific API endpoint' },
  { kind: 'team', description: 'A team or group' },
  { kind: 'event', description: 'A specific API channel operation' },
  { kind: 'step', description: 'A plain step with a custom color and icon' },
  { kind: 'flow', description: 'A link to another Flow' },
  { kind: 'link', description: 'A link to an external URL' },
]

/** API Call/Event tiles need `atlas.apis` selected in the running distribution — every other tile is always available. */
const REQUIRES_ATLAS_APIS: ReadonlySet<FlowNodeKind> = new Set(['call', 'event'])

/** Tile color per kind, matching the color its actual canvas node renders with (`FlowNodes.tsx`) — so the picker previews what a kind will look like. API Call/Event have no fixed color of their own (theirs comes from the picked Endpoint's method / Operation's direction); `GET`/`send` stand in as each kind's representative default. Component/API's real per-subtype color isn't known yet at picker time (no entity chosen), so they use `FLOW_NODE_PALETTE`'s generic color here same as before. Step is intentionally absent — see `NEUTRAL_COLORS`. */
const TILE_COLORS: Partial<Record<FlowNodeKind, FlowNodeColors>> = {
  actor: FLOW_NODE_PALETTE.actor,
  team: FLOW_NODE_PALETTE.team,
  component: FLOW_NODE_PALETTE.component,
  data: FLOW_NODE_PALETTE.data,
  api: FLOW_NODE_PALETTE.api,
  system: FLOW_NODE_PALETTE.system,
  external: FLOW_NODE_PALETTE.external,
  call: callMethodColors('GET'),
  event: eventDirectionColors('send'),
  flow: FLOW_NODE_PALETTE.flow,
  link: FLOW_NODE_PALETTE.link,
}

const tileButtonStyle = {
  display: 'flex' as const,
  flexDirection: 'column' as const,
  gap: 6,
  alignItems: 'flex-start' as const,
  width: '100%',
  boxSizing: 'border-box' as const,
  padding: 12,
  borderRadius: 8,
  textAlign: 'left' as const,
  transition: 'box-shadow 0.15s ease, transform 0.15s ease, border-color 0.15s ease',
}

/** Tile style for `kind`, including its hover/disabled state — matches the unified card anatomy every node kind now renders with: neutral fill, a bold (2px) colored border always, a lift-plus-shadow on hover. Border *width* stays fixed on hover — the button's height is auto, so `boxSizing: border-box` doesn't stop a wider border from growing the rendered box; that growth would change the grid row's height and visibly shift every other tile. Only the shadow/lift (paint-only, no layout impact) changes. */
function tileStyle(colors: FlowNodeColors, { hovered, disabled }: { hovered: boolean; disabled: boolean }) {
  const active = hovered && !disabled
  return {
    ...tileButtonStyle,
    background: 'var(--g-color-base-background)',
    border: `2px solid ${colors.border}`,
    boxShadow: active ? '0 4px 10px rgba(0, 0, 0, 0.12)' : 'none',
    transform: active ? 'translateY(-1px)' : 'none',
    opacity: disabled ? 0.5 : 1,
    cursor: disabled ? 'not-allowed' : 'pointer',
  }
}

/** The icon itself plus its `@gravity-ui/icons` component name — the icon-field trigger's "selected" content, so the chosen icon reads at a glance rather than by name alone. */
function IconOptionContent({ name }: { name: string }) {
  const iconData = gravityIconComponent(name)
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0' }}>
      {iconData && <Icon data={iconData} size={16} />}
      <Text variant="body-2">{name}</Text>
    </div>
  )
}

/** Every `@gravity-ui/icons` name, the picker grid's unfiltered browse set — matches the reference gravity-ui.com/icons page, which browses the full catalog rather than a capped subset. */
const ICON_PICKER_LIMIT = GRAVITY_ICON_NAMES.length

function iconTileStyle(selected: boolean) {
  return {
    display: 'flex' as const,
    alignItems: 'center' as const,
    justifyContent: 'center' as const,
    width: 36,
    height: 36,
    padding: 0,
    borderRadius: 6,
    border: selected ? '2px solid var(--g-color-text-primary)' : '2px solid transparent',
    background: selected ? 'var(--g-color-base-selection)' : 'transparent',
    cursor: 'pointer' as const,
  }
}

/**
 * Browsable icon grid, replacing a searchable `Select` dropdown: a search box
 * narrows the grid by name/keyword (`searchGravityIcons`), each tile shows
 * the icon alone with its component name as a native hover tooltip (a
 * Gravity `Tooltip` per tile would be needless overhead across ~800 icons),
 * and clicking a tile selects it and closes the dialog.
 */
function IconPickerDialog({ open, value, onSelect, onClose }: { open: boolean; value?: string; onSelect: (name: string) => void; onClose: () => void }) {
  const titleId = useId()
  const [filter, setFilter] = useState('')
  const names = searchGravityIcons(filter, ICON_PICKER_LIMIT)
  return (
    <Dialog open={open} onClose={onClose} aria-labelledby={titleId} size="l">
      <Dialog.Header caption="Choose icon" id={titleId} />
      <Dialog.Body>
        <TextInput value={filter} onUpdate={setFilter} placeholder="Search icons by name or keyword..." hasClear autoFocus />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(36px, 1fr))', gap: 6, marginTop: 12, maxHeight: 420, overflowY: 'auto' }}>
          {names.map((name) => {
            const iconData = gravityIconComponent(name)
            if (!iconData) return null
            return (
              <button
                key={name}
                type="button"
                title={name}
                aria-label={name}
                aria-pressed={name === value}
                onClick={() => { onSelect(name); onClose() }}
                style={iconTileStyle(name === value)}
              >
                <Icon data={iconData} size={18} />
              </button>
            )
          })}
        </div>
        {names.length === 0 && <Text color="secondary" variant="body-2">No icons match &quot;{filter}&quot;</Text>}
      </Dialog.Body>
    </Dialog>
  )
}

/** Search-as-you-type state for the API Call/Event picker's flat cross-API lookup, paginated as the author scrolls — `active` gates the fetch so only the currently-picked kind's search runs. `results`/`numPages` accumulate across pages of one debounced search term and reset whenever that term changes; `cancelledRef` (the same in-flight-cancellation pattern the fetch already used, now a ref so `loadMore`'s page fetch shares it) is flipped by the effect's cleanup on every new debounced term, so a page-2+ response that resolves after the term has already changed is discarded instead of appending onto the new term's reset results. `hasMore` is `true` until the first response's `numPages` is known, so the sentinel row renders (and can trigger `onLoadMore`) even before any page has loaded. */
function useEndpointSearch(active: boolean) {
  const [filter, setFilter] = useState('')
  const [results, setResults] = useState<EndpointSearchResult[]>([])
  const [page, setPage] = useState(1)
  const [numPages, setNumPages] = useState<number | null>(null)
  const [fetching, setFetching] = useState(false)
  const debouncedFilter = useDebouncedValue(filter, 300)
  const hasMore = numPages === null || page < numPages
  const cancelledRef = useRef(false)

  useEffect(() => {
    if (!active) return
    cancelledRef.current = false
    setResults([])
    setPage(1)
    setNumPages(null)
    setFetching(true)
    endpointsApi.search(debouncedFilter, 1)
      .then((result) => {
        if (cancelledRef.current) return
        setResults(result.page.objectList)
        setPage(result.page.number)
        setNumPages(result.numPages)
      })
      .catch(() => { if (!cancelledRef.current) setResults([]) })
      .finally(() => { if (!cancelledRef.current) setFetching(false) })
    return () => { cancelledRef.current = true }
  }, [active, debouncedFilter])

  function loadMore() {
    if (fetching || !hasMore) return
    setFetching(true)
    endpointsApi.search(debouncedFilter, page + 1)
      .then((result) => {
        if (cancelledRef.current) return
        setResults((current) => [...current, ...result.page.objectList])
        setPage(result.page.number)
        setNumPages(result.numPages)
      })
      .finally(() => { if (!cancelledRef.current) setFetching(false) })
  }

  return { filter, setFilter, results, loading: fetching || hasMore, onLoadMore: loadMore }
}

function useOperationSearch(active: boolean) {
  const [filter, setFilter] = useState('')
  const [results, setResults] = useState<OperationSearchResult[]>([])
  const [page, setPage] = useState(1)
  const [numPages, setNumPages] = useState<number | null>(null)
  const [fetching, setFetching] = useState(false)
  const debouncedFilter = useDebouncedValue(filter, 300)
  const hasMore = numPages === null || page < numPages
  const cancelledRef = useRef(false)

  useEffect(() => {
    if (!active) return
    cancelledRef.current = false
    setResults([])
    setPage(1)
    setNumPages(null)
    setFetching(true)
    operationsApi.search(debouncedFilter, 1)
      .then((result) => {
        if (cancelledRef.current) return
        setResults(result.page.objectList)
        setPage(result.page.number)
        setNumPages(result.numPages)
      })
      .catch(() => { if (!cancelledRef.current) setResults([]) })
      .finally(() => { if (!cancelledRef.current) setFetching(false) })
    return () => { cancelledRef.current = true }
  }, [active, debouncedFilter])

  function loadMore() {
    if (fetching || !hasMore) return
    setFetching(true)
    operationsApi.search(debouncedFilter, page + 1)
      .then((result) => {
        if (cancelledRef.current) return
        setResults((current) => [...current, ...result.page.objectList])
        setPage(result.page.number)
        setNumPages(result.numPages)
      })
      .finally(() => { if (!cancelledRef.current) setFetching(false) })
  }

  return { filter, setFilter, results, loading: fetching || hasMore, onLoadMore: loadMore }
}

/** Mirrors `useEndpointSearch`/`useOperationSearch` above, backed by `flowsApi.list({q, page})` instead of a dedicated search endpoint — Flow's own list endpoint already supports `q` free-text search. The Flow currently being edited may appear among its results; the "Flow reference lookup" requirement explicitly allows selecting it (not an error). */
function useFlowSearch(active: boolean) {
  const [filter, setFilter] = useState('')
  const [results, setResults] = useState<FlowEntity[]>([])
  const [page, setPage] = useState(1)
  const [numPages, setNumPages] = useState<number | null>(null)
  const [fetching, setFetching] = useState(false)
  const debouncedFilter = useDebouncedValue(filter, 300)
  const hasMore = numPages === null || page < numPages
  const cancelledRef = useRef(false)

  useEffect(() => {
    if (!active) return
    cancelledRef.current = false
    setResults([])
    setPage(1)
    setNumPages(null)
    setFetching(true)
    flowsApi.list({ q: debouncedFilter, page: 1 })
      .then((result) => {
        if (cancelledRef.current) return
        setResults(result.page.objectList)
        setPage(result.page.number)
        setNumPages(result.numPages)
      })
      .catch(() => { if (!cancelledRef.current) setResults([]) })
      .finally(() => { if (!cancelledRef.current) setFetching(false) })
    return () => { cancelledRef.current = true }
  }, [active, debouncedFilter])

  function loadMore() {
    if (fetching || !hasMore) return
    setFetching(true)
    flowsApi.list({ q: debouncedFilter, page: page + 1 })
      .then((result) => {
        if (cancelledRef.current) return
        setResults((current) => [...current, ...result.page.objectList])
        setPage(result.page.number)
        setNumPages(result.numPages)
      })
      .finally(() => { if (!cancelledRef.current) setFetching(false) })
  }

  return { filter, setFilter, results, loading: fetching || hasMore, onLoadMore: loadMore }
}

export interface FlowStepModalProps {
  open: boolean
  /** All current steps — used for fresh-id generation and id-uniqueness validation. */
  steps: FlowStep[]
  /** Step being edited; `null` means Add Step mode. */
  step: FlowStep | null
  /** The single ref-status entry for `step` — not the whole Flow's map. Undefined in Add Step mode, or when the step's ref has no live status. */
  refStatus?: FlowStepRefStatus
  onClose: () => void
  /** `previousId` is the step's id before this save, or `null` when adding — lets the caller cascade an id rename. */
  onSave: (step: FlowStep, previousId: string | null) => void
}

/** Node-type picker (Add Step) + edit/retype modal (existing node), sharing one dialog. */
export function FlowStepModal({ open, steps, step, refStatus, onClose, onSave }: FlowStepModalProps) {
  const titleId = useId()
  const [pickedKind, setPickedKind] = useState<FlowNodeKind | null>(null)
  const [id, setId] = useState('')
  const [title, setTitle] = useState('')
  const [summary, setSummary] = useState('')
  const [entityRef, setEntityRef] = useState<string | null>(null)
  const [color, setColor] = useState<FlowStepLabelTheme | undefined>(undefined)
  const [icon, setIcon] = useState<string | undefined>(undefined)
  const [typeLabel, setTypeLabel] = useState('')
  const [iconPickerOpen, setIconPickerOpen] = useState(false)
  const [externalLabel, setExternalLabel] = useState('')
  const [queryRef, setQueryRef] = useState<FlowStepQueryRef | null>(null)
  const [eventRef, setEventRef] = useState<FlowStepEventRef | null>(null)
  const [flowRef, setFlowRef] = useState<number | null>(null)
  const [linkUrl, setLinkUrl] = useState('')
  const [hoveredKind, setHoveredKind] = useState<FlowNodeKind | null>(null)
  // Optimistic default (assume available) so the tiles don't flash disabled
  // before the health check resolves — `isAtlasApisAvailable()` itself fails
  // closed on a fetch error.
  const [apisAvailable, setApisAvailable] = useState(true)

  const endpointSearch = useEndpointSearch(open && pickedKind === 'call')
  const operationSearch = useOperationSearch(open && pickedKind === 'event')
  const flowSearch = useFlowSearch(open && pickedKind === 'flow')
  const entityCatalog = useFlowEntityCatalog()
  // Same-session fallback for the selected Flow's name/description, both for
  // the picker/lookup's pinned-selection row (below) and the in-modal stale
  // warning (mirroring `FlowNodeComponent`'s canvas-card use of the
  // same hook) — a step with no server-resolved `refStatus` entry yet (just
  // added, or just re-pointed at a different Flow, this session).
  const flowRefDetails = useFlowRefDetails(refStatus?.name !== undefined ? undefined : flowRef)

  useEffect(() => {
    if (!open) return
    let cancelled = false
    isAtlasApisAvailable().then((available) => { if (!cancelled) setApisAvailable(available) })
    return () => { cancelled = true }
  }, [open])

  useEffect(() => {
    if (!open) return
    setIconPickerOpen(false)
    if (step) {
      setPickedKind(flowNodeKindOf(step))
      setId(step.id)
      setTitle(step.title ?? '')
      setSummary(step.summary ?? '')
      setEntityRef(step.entity_ref ?? null)
      // `color` wins; an unmigrated flow's `label_theme` maps onto the swatch
      // of the same name so editing an
      // old Step shows its actual rendered color, not a blank default.
      setColor(step.color ?? (step.label_theme ? LABEL_THEME_TO_COLOR[step.label_theme] : undefined))
      setIcon(step.icon)
      setTypeLabel(step.type_label ?? '')
      setExternalLabel(step.external_label ?? '')
      setQueryRef(step.query_ref ?? null)
      setEventRef(step.event_ref ?? null)
      setFlowRef(step.flow_ref ?? null)
      setLinkUrl(step.link_url ?? '')
    } else {
      setPickedKind(null)
      setId(nextFlowStepId(steps))
      setTitle('')
      setSummary('')
      setEntityRef(null)
      setColor(undefined)
      setIcon(undefined)
      setTypeLabel('')
      setExternalLabel('')
      setQueryRef(null)
      setEventRef(null)
      setFlowRef(null)
      setLinkUrl('')
    }
    // Re-seed only when the dialog opens or the target step changes, not on every `steps` edit elsewhere.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, step])

  /** Pulls `refStatus.live`'s direction/channel/summary into the in-memory `eventRef` form state — writes to component state only, never persisted until the author clicks Save. Each field only overwritten when it's actually present on `live` (direction/channel always come as a pair; summary is independent). No-op without an active drift signal. */
  function refreshEventRef() {
    if (!refStatus?.live) return
    const live = refStatus.live
    setEventRef((current) => {
      if (!current) return current
      const next = { ...current }
      if (live.direction !== undefined && live.channel_address !== undefined) {
        next.direction = live.direction
        next.channel = live.channel_address
      }
      if (live.summary !== undefined) next.summary = live.summary
      return next
    })
  }

  /** Mirrors `refreshEventRef`, for a Call step's `query_ref` — only `summary` can ever be on `live` here, since `method`/`path` cannot drift by construction. */
  function refreshQueryRef() {
    if (!refStatus?.live?.summary) return
    const summary = refStatus.live.summary
    setQueryRef((current) => (current ? { ...current, summary } : current))
  }

  function selectKind(kind: FlowNodeKind) {
    if (REQUIRES_ATLAS_APIS.has(kind) && !apisAvailable) return
    setPickedKind(kind)
    setEntityRef(null)
    setColor(undefined)
    setIcon(undefined)
    setTypeLabel('')
    setIconPickerOpen(false)
    setExternalLabel('')
    setQueryRef(null)
    setEventRef(null)
    setFlowRef(null)
    setLinkUrl('')
  }

  function changeType() {
    setPickedKind(null)
    setEntityRef(null)
    setColor(undefined)
    setIcon(undefined)
    setTypeLabel('')
    setIconPickerOpen(false)
    setExternalLabel('')
    setQueryRef(null)
    setEventRef(null)
    setFlowRef(null)
    setLinkUrl('')
  }

  const trimmedId = id.trim()
  const entityKind = pickedKind && isEntityNodeKind(pickedKind) ? pickedKind : null
  // A ref-backed step (entity_ref, query_ref, event_ref, or flow_ref) never carries a custom
  // title/summary — its card always renders text derived from the reference itself instead
  // the referenced entity's live title/description for entity_ref, the
  // snapshotted method/path or channel/direction for query_ref/event_ref, or the referenced
  // Flow's live name/description for flow_ref (Flow joins the ref-backed
  // family; Link stays freeform like External/Step).
  const refBackedKind = Boolean(entityKind) || pickedKind === 'call' || pickedKind === 'event' || pickedKind === 'flow'
  const trimmedLinkUrl = linkUrl.trim()
  const kindError = pickedKind === 'external' && !externalLabel.trim()
    ? 'Enter a label for this external reference'
    : entityKind && !entityRef
      ? `Select a ${FLOW_NODE_KIND_LABELS[entityKind]}`
      : pickedKind === 'call' && !queryRef
        ? 'Select an Endpoint'
        : pickedKind === 'event' && !eventRef
          ? 'Select an Operation'
          : pickedKind === 'flow' && !flowRef
            ? 'Select a Flow'
            : pickedKind === 'link' && !isHttpUrl(trimmedLinkUrl)
              ? 'Enter a valid http(s) URL'
              : null
  const canSave = pickedKind !== null && !kindError

  function handleSave() {
    if (!canSave || !pickedKind) return
    const next: FlowStep = {
      ...step,
      id: trimmedId,
      // Enforced here too, not just by the modal having no Title/Summary inputs for these
      // kinds, so a step already carrying stale title/summary (pre-existing, or
      // a kind switch) never round-trips them back out on save.
      title: refBackedKind ? undefined : (title.trim() || undefined),
      summary: refBackedKind ? undefined : (summary.trim() || undefined),
      entity_ref: entityKind ? entityRef : undefined,
      // Saving any step writes `color` (defaulting an unset Step's to
      // `DEFAULT_STEP_THEME`) and drains `label_theme` away for good, per
      // the migration plan — a step's stored shape never
      // round-trips through the deprecated field again once edited here.
      color: pickedKind === 'step' ? (color ?? DEFAULT_STEP_THEME) : undefined,
      label_theme: undefined,
      icon: pickedKind === 'step' ? icon : undefined,
      type_label: pickedKind === 'step' ? (typeLabel.trim() || undefined) : undefined,
      external_label: pickedKind === 'external' ? externalLabel.trim() : undefined,
      query_ref: pickedKind === 'call' ? (queryRef ?? undefined) : undefined,
      event_ref: pickedKind === 'event' ? (eventRef ?? undefined) : undefined,
      flow_ref: pickedKind === 'flow' ? (flowRef ?? undefined) : undefined,
      link_url: pickedKind === 'link' ? trimmedLinkUrl : undefined,
    }
    onSave(next, step ? step.id : null)
    onClose()
  }

  // Same tooltip the canvas card shows for this step —
  // `refStatus` is only ever passed for the step currently being edited, so
  // no `pickedKind` guard is needed here beyond what the render site itself
  // already applies.
  const eventRefTooltip = staleRefTooltip(refStatus, 'operation')
  const queryRefTooltip = staleRefTooltip(refStatus, 'endpoint')
  // Mirrors `FlowNodeComponent`'s canvas-card warning (the same warning icon/tooltip
  // also renders inside the step-edit modal).
  const flowRefTooltip = staleFlowRefTooltip(refStatus, flowRefDetails)

  // Filtered to the ref kind matching the selected node type — reads the page-scoped catalog instead of each
  // modal mount fetching its own capped page via `RefSelect`.
  const entityRefKind = entityKind ? ENTITY_KIND_TO_REF_KIND[entityKind] : null
  const entityOptions = entityKind && entityRefKind
    ? entityCatalog.itemsByKind[entityRefKind].map((item) => {
        const primary = item.metadata.title || item.metadata.name
        return {
          value: `${entityRefKind}:${item.metadata.name}`,
          text: primary,
          content: (
            <LookupOptionRow
              icon={<Icon data={FLOW_NODE_KIND_ICONS[entityKind]} size={16} />}
              primary={primary}
              secondary={item.metadata.name}
            />
          ),
        }
      })
    : []

  // Pins the currently-selected result at the top of the options list even
  // when a fresh search hasn't (yet) returned it — e.g. editing an existing
  // step whose Endpoint isn't among the latest search results.
  const queryOptions = [
    ...(queryRef && !endpointSearch.results.some((result) => result.endpoint.id === queryRef.endpoint)
      ? [{
          value: queryRef.endpoint,
          // `text` (not `content`, a ReactElement here) is what the closed
          // control's selected-value label falls back to — without it, Select
          // falls back further to the raw option `value` (the endpoint's UUID).
          text: `${queryRef.method} ${queryRef.path}`,
          content: <LookupOptionRow primary={`${queryRef.method} ${queryRef.path}`} secondary={refName(queryRef.api)} />,
        }]
      : []),
    ...endpointSearch.results.map((result) => ({
      value: result.endpoint.id,
      text: `${result.endpoint.method} ${result.endpoint.path}`,
      content: <LookupOptionRow primary={`${result.endpoint.method} ${result.endpoint.path}`} secondary={result.api.title || result.api.name} />,
    })),
  ]

  const eventOptions = [
    ...(eventRef && !operationSearch.results.some((result) => result.operation.id === eventRef.operation)
      ? [{
          value: eventRef.operation,
          text: eventRef.channel,
          content: <LookupOptionRow primary={eventRef.channel} secondary={refName(eventRef.api)} />,
        }]
      : []),
    ...operationSearch.results.map((result) => ({
      value: result.operation.id,
      text: result.operation.channelAddress,
      content: <LookupOptionRow primary={result.operation.channelAddress} secondary={result.api.title || result.api.name} />,
    })),
  ]

  // Mirrors `queryOptions`/`eventOptions` above: pins the currently-selected Flow at the top
  // even when a fresh search hasn't (yet) returned it. Unlike `query_ref`/`event_ref`, a
  // `flow_ref` is only an id — no snapshotted name/description travels with it — so the pinned
  // row's text falls back through the server-resolved `refStatus.name`/`description`
  // and this same-session `flowRefDetails` fetch (`useFlowRefDetails`) before a bare "Flow #id"
  // placeholder for a reference neither has resolved yet.
  const selectedFlowName = refStatus?.name || flowRefDetails?.name || (flowRef !== null ? `Flow #${flowRef}` : '')
  const selectedFlowDescription = refStatus?.description || flowRefDetails?.description || ''
  const flowOptions = [
    ...(flowRef !== null && !flowSearch.results.some((flow) => flow.id === flowRef)
      ? [{
          value: String(flowRef),
          text: selectedFlowName,
          content: <LookupOptionRow icon={<Icon data={FLOW_NODE_KIND_ICONS.flow} size={16} />} primary={selectedFlowName} secondary={selectedFlowDescription} />,
        }]
      : []),
    ...flowSearch.results.map((flow) => ({
      value: String(flow.id),
      text: flow.name,
      content: <LookupOptionRow icon={<Icon data={FLOW_NODE_KIND_ICONS.flow} size={16} />} primary={flow.name} secondary={flow.description} />,
    })),
  ]

  return (
    <Dialog open={open} onClose={onClose} aria-labelledby={titleId} size="m">
      <Dialog.Header caption={step ? 'Edit step' : 'Add step'} id={titleId} />
      <Dialog.Body>
        {pickedKind === null ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12, paddingBottom: 12 }}>
            {KIND_TILES.map(({ kind, description }) => {
              const disabled = REQUIRES_ATLAS_APIS.has(kind) && !apisAvailable
              const colors = TILE_COLORS[kind] ?? NEUTRAL_COLORS
              const tile = (
                <button
                  key={kind}
                  type="button"
                  // `aria-disabled` (not the native `disabled` attribute) so the
                  // wrapping Tooltip below still receives hover events — a
                  // disabled form control doesn't fire mouse/pointer events in
                  // Chrome/Firefox, which would silently swallow the tooltip
                  // that's the whole point of this state.
                  aria-disabled={disabled}
                  onClick={() => selectKind(kind)}
                  onMouseEnter={() => setHoveredKind(kind)}
                  onMouseLeave={() => setHoveredKind((prev) => (prev === kind ? null : prev))}
                  style={tileStyle(colors, { hovered: hoveredKind === kind, disabled })}
                >
                  <div style={{ alignSelf: 'flex-start' }}>
                    <Label theme={colors.theme} size="xs" icon={<Icon data={FLOW_NODE_KIND_ICONS[kind]} size={12} />}>
                      {FLOW_NODE_KIND_LABELS[kind]}
                    </Label>
                  </div>
                  <Text color="secondary" variant="caption-2">{description}</Text>
                </button>
              )
              // External additionally gets its own explanatory tooltip (task
              // 7.1), distinguishing it from the catalog's unrelated
              // `External` tag — disabled always wins since only one Tooltip
              // can wrap a tile, and every other kind's own reason not to
              // hover-explain still applies.
              if (disabled) return <Tooltip key={kind} content="Requires the APIs plugin" placement="top">{tile}</Tooltip>
              if (kind === 'external') return <Tooltip key={kind} content={EXTERNAL_KIND_HELP_TEXT} placement="top">{tile}</Tooltip>
              return tile
            })}
          </div>
        ) : (
          <div style={{ display: 'grid', gap: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Label size="m">{FLOW_NODE_KIND_LABELS[pickedKind]}</Label>
              <Button size="s" view="flat" onClick={changeType}>Change type</Button>
            </div>
            {!refBackedKind && (
              <>
                <div>
                  <Text color="secondary">Title</Text>
                  <TextInput value={title} onUpdate={setTitle} placeholder="Title (optional)" />
                </div>
                <div>
                  <Text color="secondary">Summary</Text>
                  <TextArea value={summary} onUpdate={setSummary} placeholder="Summary (optional)" minRows={2} />
                </div>
              </>
            )}
            {entityKind && (
              <div>
                <Text color="secondary">{FLOW_NODE_KIND_LABELS[entityKind]}</Text>
                <Select
                  placeholder={`Select a ${FLOW_NODE_KIND_LABELS[entityKind]}`}
                  filterable
                  filterPlaceholder="Search by name..."
                  value={entityRef ? [entityRef] : []}
                  onUpdate={(next) => setEntityRef(next[0] ?? null)}
                  options={entityOptions}
                  {...lookupSelectLoadingProps(entityCatalog.isLoading)}
                  hasClear
                  width="max"
                />
              </div>
            )}
            {pickedKind === 'call' && (
              <div>
                {/* Mirrors the Event block below — same shared components
                  (`FlowRefWarning.tsx`), refresh only ever pulls `summary` here since
                  a query_ref's method/path cannot drift by construction. */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Text color="secondary">Endpoint</Text>
                  {queryRefTooltip && <StaleRefWarning tooltip={queryRefTooltip} />}
                  {refStatus?.live?.summary !== undefined && <RefreshRefButton onClick={refreshQueryRef} label="Refresh from live endpoint" />}
                </div>
                <Select
                  placeholder="Search endpoints..."
                  filterable
                  filterPlaceholder="Search by path, summary, or operation id..."
                  filter={endpointSearch.filter}
                  onFilterChange={endpointSearch.setFilter}
                  value={queryRef ? [queryRef.endpoint] : []}
                  onUpdate={(next) => {
                    const selectedId = next[0]
                    const result = endpointSearch.results.find((item) => item.endpoint.id === selectedId)
                    setQueryRef(result
                      ? { api: result.api.ref, endpoint: result.endpoint.id, method: result.endpoint.method, path: result.endpoint.path, summary: result.endpoint.summary }
                      : null)
                  }}
                  options={queryOptions}
                  onLoadMore={endpointSearch.onLoadMore}
                  {...lookupSelectLoadingProps(endpointSearch.loading)}
                  hasClear
                  width="max"
                />
              </div>
            )}
            {pickedKind === 'event' && (
              <div>
                {/* Mirrors the canvas card's warning + refresh control — same shared components (`FlowRefWarning.tsx`), same
                  tooltip copy, same visibility rule (refresh only when `refStatus.live` is set). */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Text color="secondary">Operation</Text>
                  {eventRefTooltip && <StaleRefWarning tooltip={eventRefTooltip} />}
                  {refStatus?.live && <RefreshRefButton onClick={refreshEventRef} />}
                </div>
                <Select
                  placeholder="Search operations..."
                  filterable
                  filterPlaceholder="Search by channel, summary, or operation id..."
                  filter={operationSearch.filter}
                  onFilterChange={operationSearch.setFilter}
                  value={eventRef ? [eventRef.operation] : []}
                  onUpdate={(next) => {
                    const selectedId = next[0]
                    const result = operationSearch.results.find((item) => item.operation.id === selectedId)
                    setEventRef(result
                      ? { api: result.api.ref, operation: result.operation.id, direction: result.operation.direction, channel: result.operation.channelAddress, summary: result.operation.summary }
                      : null)
                  }}
                  options={eventOptions}
                  onLoadMore={operationSearch.onLoadMore}
                  {...lookupSelectLoadingProps(operationSearch.loading)}
                  hasClear
                  width="max"
                />
              </div>
            )}
            {pickedKind === 'flow' && (
              <div>
                {/* Mirrors the Call/Event blocks above — same shared `StaleRefWarning`
                  (`FlowRefWarning.tsx`)/`staleFlowRefTooltip` (`FlowNodes.tsx`) the canvas
                  card uses, so the same warning renders here too. Flow has no drift/refresh
                  control of its own — a Flow reference doesn't snapshot anything to drift. */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Text color="secondary">Flow</Text>
                  {flowRefTooltip && <StaleRefWarning tooltip={flowRefTooltip} />}
                </div>
                <Select
                  placeholder="Search Flows..."
                  filterable
                  filterPlaceholder="Search by name..."
                  filter={flowSearch.filter}
                  onFilterChange={flowSearch.setFilter}
                  value={flowRef !== null ? [String(flowRef)] : []}
                  onUpdate={(next) => {
                    const selectedId = next[0]
                    // Clearing the lookup reverts the node to the plain Step type, not just
                    // an empty Flow selection ("Flow reference lookup" requirement's "Clear a
                    // Flow reference" scenario) — unlike clearing an entity_ref/query_ref/
                    // event_ref lookup, which just leaves this picked kind unselected.
                    if (!selectedId) {
                      setFlowRef(null)
                      setPickedKind('step')
                      return
                    }
                    setFlowRef(Number(selectedId))
                  }}
                  options={flowOptions}
                  onLoadMore={flowSearch.onLoadMore}
                  {...lookupSelectLoadingProps(flowSearch.loading)}
                  hasClear
                  width="max"
                />
              </div>
            )}
            {pickedKind === 'external' && (
              <div>
                <Text color="secondary">Label</Text>
                <TextInput value={externalLabel} onUpdate={setExternalLabel} placeholder="e.g. Payment Gateway" />
              </div>
            )}
            {pickedKind === 'link' && (
              <div>
                <Text color="secondary">URL</Text>
                <TextInput value={linkUrl} onUpdate={setLinkUrl} placeholder="https://example.com" />
              </div>
            )}
            {pickedKind === 'step' && (
              <>
                <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start' }}>
                  <div>
                    <Text color="secondary">Color</Text>
                    <div style={{ display: 'flex', gap: 10, marginTop: 6 }}>
                      {STEP_SWATCH_THEMES.map((theme) => {
                        const swatch = FLOW_NODE_SWATCHES[theme]
                        const selected = (color ?? DEFAULT_STEP_THEME) === theme
                        return (
                          <Tooltip key={theme} content={theme} placement="top">
                            <button
                              type="button"
                              aria-label={theme}
                              aria-pressed={selected}
                              onClick={() => setColor(theme)}
                              style={{
                                width: 28,
                                height: 28,
                                padding: 0,
                                borderRadius: '50%',
                                background: swatch.border,
                                border: selected ? '2px solid var(--g-color-text-primary)' : '2px solid transparent',
                                boxShadow: selected ? '0 0 0 2px var(--g-color-base-background)' : 'none',
                                cursor: 'pointer',
                              }}
                            />
                          </Tooltip>
                        )
                      })}
                    </div>
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <Text color="secondary">Icon</Text>
                    <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
                      <Button view="outlined" size="m" width="max" onClick={() => setIconPickerOpen(true)} style={{ justifyContent: 'flex-start' }}>
                        {icon ? <IconOptionContent name={icon} /> : <Text color="hint" variant="body-2">Default step icon</Text>}
                      </Button>
                      {icon && (
                        <Button view="flat" size="m" aria-label="Clear icon" onClick={() => setIcon(undefined)}>
                          <Icon data={Xmark} size={16} />
                        </Button>
                      )}
                    </div>
                    <IconPickerDialog open={iconPickerOpen} value={icon} onSelect={setIcon} onClose={() => setIconPickerOpen(false)} />
                  </div>
                </div>
                <div>
                  <Text color="secondary">Type label</Text>
                  <TextInput value={typeLabel} onUpdate={setTypeLabel} placeholder="Step" />
                </div>
              </>
            )}
            {kindError && <Text color="danger" variant="caption-2">{kindError}</Text>}
          </div>
        )}
      </Dialog.Body>
      {pickedKind !== null && (
        <Dialog.Footer
          textButtonApply={step ? 'Save' : 'Add'}
          textButtonCancel="Cancel"
          onClickButtonCancel={onClose}
          onClickButtonApply={handleSave}
          propsButtonApply={{ disabled: !canSave }}
        />
      )}
    </Dialog>
  )
}
