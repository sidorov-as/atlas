import type { FlowStep, FlowStepLabelTheme, FlowStepRefStatus, FlowStepTransition } from '../lib/flowLayout'
import { isGravityIconName } from '../lib/gravityIcons'

export interface FlowStepsParseResult { steps: FlowStep[] | null; error: string | null }
const STEP_KEYS = new Set(['id', 'title', 'summary', 'entity_ref', 'next_step', 'next_steps', 'position', 'label_theme', 'color', 'icon', 'type_label', 'external_label', 'query_ref', 'event_ref', 'flow_ref', 'link_url'])
// Mirrors `apps/catalog/models/flow.py`'s `LABEL_THEMES`.
const LABEL_THEMES = new Set<FlowStepLabelTheme>(['success', 'danger', 'warning', 'info', 'utility', 'normal'])
// `color` shares `label_theme`'s six-name vocabulary.
const STEP_COLORS = new Set<FlowStepLabelTheme>(['success', 'danger', 'warning', 'info', 'utility', 'normal'])
// Mirrors `apps/catalog/models/flow.py`'s `QUERY_REF_KEYS`/`EVENT_REF_KEYS`.
const QUERY_REF_KEYS = new Set(['api', 'endpoint', 'method', 'path'])
const EVENT_REF_KEYS = new Set(['api', 'operation', 'direction', 'channel'])
// Mirrors `apps/catalog/models/flow.py`'s `REF_OPTIONAL_KEYS` — the picked Endpoint's/Operation's own `summary` at pick time,
// optional and empty-string-allowed since the Endpoint/Operation's own `summary` is itself optional.
const REF_OPTIONAL_KEYS = new Set(['summary'])
function isTransition(value: unknown): value is FlowStepTransition { return Boolean(value) && typeof value === 'object' && typeof (value as { id?: unknown }).id === 'string' }
/** Mirrors `models.py`'s `_LINK_URL_VALIDATOR`: a well-formed absolute http(s) URL, rejecting other schemes (e.g. `javascript:`). Exported so `FlowStepModal.tsx`'s Link URL field validates with this exact rule instead of a second copy. */
export function isHttpUrl(value: string): boolean {
  try {
    return ['http:', 'https:'].includes(new URL(value).protocol)
  } catch {
    return false
  }
}
function isPosition(value: unknown): value is { x: number; y: number } {
  if (!value || typeof value !== 'object') return false
  const record = value as Record<string, unknown>
  return Object.keys(record).length === 2 && typeof record.x === 'number' && typeof record.y === 'number'
}
/** Shape-checks a `query_ref`/`event_ref`: a dict with exactly `expectedKeys` (each a non-empty string) plus, optionally, any of `REF_OPTIONAL_KEYS` (each a string, empty allowed) — mirrors `models.py`'s `_validate_ref_shape`. */
function isRefShape(value: unknown, expectedKeys: Set<string>): value is Record<string, string> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false
  const record = value as Record<string, unknown>
  const keys = Object.keys(record)
  return keys.every((key) => expectedKeys.has(key) || REF_OPTIONAL_KEYS.has(key))
    && [...expectedKeys].every((key) => keys.includes(key))
    && [...expectedKeys].every((key) => typeof record[key] === 'string' && record[key])
    && [...REF_OPTIONAL_KEYS].every((key) => !(key in record) || typeof record[key] === 'string')
}

/** Parses the persisted Flow JSON grammar without changing its API representation. */
export function parseFlowSteps(text: string): FlowStepsParseResult {
  try {
    const value: unknown = JSON.parse(text)
    if (!Array.isArray(value)) return { steps: null, error: 'steps must be a JSON array' }
    for (const [index, step] of value.entries()) {
      if (!step || typeof step !== 'object' || Array.isArray(step)) return { steps: null, error: `Step ${index + 1} must be an object` }
      const record = step as Record<string, unknown>
      if (typeof record.id !== 'string') return { steps: null, error: `Step ${index + 1} must have a string id` }
      if (Object.keys(record).some((key) => !STEP_KEYS.has(key))) return { steps: null, error: `Step ${record.id || index + 1} has unsupported fields` }
      if (record.title !== undefined && typeof record.title !== 'string') return { steps: null, error: `Step ${record.id} title must be a string` }
      if (record.summary !== undefined && typeof record.summary !== 'string') return { steps: null, error: `Step ${record.id} summary must be a string` }
      if (record.entity_ref !== undefined && record.entity_ref !== null && typeof record.entity_ref !== 'string') return { steps: null, error: `Step ${record.id} entity_ref must be a string or null` }
      if (record.next_step !== undefined && record.next_step !== null && !isTransition(record.next_step)) return { steps: null, error: `Step ${record.id} next_step must have an id` }
      if (record.next_steps !== undefined && (!Array.isArray(record.next_steps) || !record.next_steps.every(isTransition))) return { steps: null, error: `Step ${record.id} next_steps must contain transition ids` }
      if (record.position !== undefined && !isPosition(record.position)) return { steps: null, error: `Step ${record.id} position must be {x: number, y: number}` }
      if (record.label_theme !== undefined && !LABEL_THEMES.has(record.label_theme as FlowStepLabelTheme)) return { steps: null, error: `Step ${record.id} has an invalid label_theme: ${String(record.label_theme)}` }
      if (record.color !== undefined && !STEP_COLORS.has(record.color as FlowStepLabelTheme)) return { steps: null, error: `Step ${record.id} has an invalid color: ${String(record.color)}` }
      if (record.icon !== undefined && (typeof record.icon !== 'string' || !isGravityIconName(record.icon))) return { steps: null, error: `Step ${record.id} has an invalid icon: ${String(record.icon)}` }
      if (record.type_label !== undefined && typeof record.type_label !== 'string') return { steps: null, error: `Step ${record.id} type_label must be a string` }
      if (record.external_label !== undefined && typeof record.external_label !== 'string') return { steps: null, error: `Step ${record.id} external_label must be a string` }
      if (record.query_ref !== undefined && record.query_ref !== null && !isRefShape(record.query_ref, QUERY_REF_KEYS)) return { steps: null, error: `Step ${record.id} query_ref must have non-empty string fields {api, endpoint, method, path}` }
      if (record.event_ref !== undefined && record.event_ref !== null && !isRefShape(record.event_ref, EVENT_REF_KEYS)) return { steps: null, error: `Step ${record.id} event_ref must have non-empty string fields {api, operation, direction, channel}` }
      if (record.flow_ref !== undefined && record.flow_ref !== null && typeof record.flow_ref !== 'number') return { steps: null, error: `Step ${record.id} flow_ref must be a number` }
      if (record.link_url !== undefined && (typeof record.link_url !== 'string' || !isHttpUrl(record.link_url))) return { steps: null, error: `Step ${record.id} link_url must be a well-formed http(s) URL` }
      if ((record.entity_ref || record.query_ref || record.event_ref || record.flow_ref) && (record.title || record.summary)) return { steps: null, error: `Step ${record.id} has an entity_ref/query_ref/event_ref/flow_ref and cannot also have a title or summary` }
      const present = ['entity_ref', 'external_label', 'query_ref', 'event_ref', 'flow_ref', 'link_url'].filter((key) => record[key])
      if (present.length > 1) return { steps: null, error: `Step ${record.id} cannot have more than one of entity_ref, external_label, query_ref, event_ref, flow_ref, link_url (has ${present.join(', ')})` }
    }
    return { steps: value as FlowStep[], error: null }
  } catch (error) { return { steps: null, error: error instanceof Error ? error.message : 'Invalid JSON' } }
}
export function serializeFlowSteps(steps: FlowStep[]): string { return JSON.stringify(steps, null, 2) }
export function nextFlowStepId(steps: FlowStep[]): string { const used = new Set(steps.map((step) => step.id)); let number = steps.length + 1; while (used.has(`step-${number}`)) number += 1; return `step-${number}` }
export function transitionTargets(step: FlowStep): string[] { return [step.next_step?.id, ...(step.next_steps ?? []).map((transition) => transition.id)].filter((id): id is string => Boolean(id)) }

/** Mirrors the backend's ID/target/acyclic-graph invariants for immediate visual feedback. */
export function validateFlowSteps(steps: FlowStep[]): string[] {
  const errors: string[] = []; const ids = new Set<string>()
  for (const step of steps) { if (!step.id.trim()) errors.push('Every step must have an id'); else if (ids.has(step.id)) errors.push(`Duplicate step id: ${step.id}`); else ids.add(step.id) }
  const adjacency = new Map<string, string[]>()
  for (const step of steps) { const targets = transitionTargets(step); adjacency.set(step.id, targets); for (const target of targets) { if (!ids.has(target)) errors.push(`Step ${step.id} transitions to unknown step id ${target}`) } }
  const visiting = new Set<string>(); const visited = new Set<string>()
  function visit(id: string): void { if (visiting.has(id)) { errors.push(`Transition from ${id} introduces a cycle`); return }; if (visited.has(id)) return; visiting.add(id); for (const target of adjacency.get(id) ?? []) if (ids.has(target)) visit(target); visiting.delete(id); visited.add(id) }
  for (const id of ids) visit(id)
  return [...new Set(errors)]
}
export function canUseTransition(steps: FlowStep[], sourceId: string, targetId: string): string | null { const source = steps.find((step) => step.id === sourceId); if (!source || !steps.some((step) => step.id === targetId)) return 'Choose an existing step as the target'; const withoutSource = steps.map((step) => step.id === sourceId ? { ...step, next_step: undefined, next_steps: [] } : step); const candidate = withoutSource.map((step) => step.id === sourceId ? { ...step, next_step: { id: targetId } } : step); return validateFlowSteps(candidate).find((error) => error.includes('unknown') || error.includes('cycle')) ?? null }

/** Adds a source→target transition, appending as a branch when the source already has one (canvas drag-to-connect). A duplicate of an existing target is a no-op. */
export function addTransition(steps: FlowStep[], sourceId: string, targetId: string): FlowStep[] {
  return steps.map((step) => {
    if (step.id !== sourceId) return step
    if (step.next_steps !== undefined) {
      return step.next_steps.some((transition) => transition.id === targetId)
        ? step
        : { ...step, next_steps: [...step.next_steps, { id: targetId }] }
    }
    if (step.next_step) {
      return step.next_step.id === targetId ? step : { ...step, next_step: undefined, next_steps: [step.next_step, { id: targetId }] }
    }
    return { ...step, next_step: { id: targetId } }
  })
}

/**
 * Adds a brand-new step, connected as `sourceId`'s outgoing transition (a new
 * branch if it already has one, via `addTransition`), at the given `position`
 * Shared by the node-header add control and
 * the add-next placeholder — callers
 * compute `position` via `resolveConnectedPosition` (`flowLayout.ts`) so it
 * lands one layout-step past the source without landing on top of another
 * node already occupying that slot.
 */
export function addConnectedStep(
  steps: FlowStep[],
  sourceId: string,
  newStep: FlowStep,
  position: { x: number; y: number },
): FlowStep[] {
  return addTransition([...steps, { ...newStep, position }], sourceId, newStep.id)
}

/** Updates the label of one source→target transition (canvas edge-click modal). A blank label clears it. */
export function updateTransitionLabel(steps: FlowStep[], sourceId: string, targetId: string, label: string): FlowStep[] {
  const trimmed = label.trim()
  return steps.map((step) => {
    if (step.id !== sourceId) return step
    if (step.next_step?.id === targetId) return { ...step, next_step: { ...step.next_step, label: trimmed || undefined } }
    if (step.next_steps) return { ...step, next_steps: step.next_steps.map((transition) => transition.id === targetId ? { ...transition, label: trimmed || undefined } : transition) }
    return step
  })
}

/** Removes one source→target transition without touching either endpoint step (canvas edge-click modal). */
export function removeTransition(steps: FlowStep[], sourceId: string, targetId: string): FlowStep[] {
  return steps.map((step) => {
    if (step.id !== sourceId) return step
    if (step.next_step?.id === targetId) return { ...step, next_step: undefined }
    if (step.next_steps) return { ...step, next_steps: step.next_steps.filter((transition) => transition.id !== targetId) }
    return step
  })
}

/**
 * Applies a step's live drift values (its `FlowStepRefStatus.live`, from `resolve_step_ref_statuses`)
 * directly onto its stored `query_ref`/`event_ref` — the canvas card's `↻` control now applies
 * immediately, the same way `removeSteps`/`addTransition`/`removeTransition` already do, rather than
 * routing through the edit modal first: it's
 * exactly as reversible as any other canvas edit, undone by simply not saving the Flow. `query_ref`
 * only ever has `live.summary` to apply (its `method`/`path` cannot drift by construction);
 * `event_ref` applies `direction`/`channel` as a pair when both are present, and `summary`
 * independently of that pair. A no-op (returns `steps` unchanged) when `live` is unset, the step
 * doesn't exist, or it has neither ref.
 */
export function refreshStepRef(steps: FlowStep[], stepId: string, live: FlowStepRefStatus['live']): FlowStep[] {
  if (!live) return steps
  return steps.map((step) => {
    if (step.id !== stepId) return step
    if (step.query_ref) {
      return live.summary !== undefined ? { ...step, query_ref: { ...step.query_ref, summary: live.summary } } : step
    }
    if (step.event_ref) {
      const next = { ...step.event_ref }
      let changed = false
      if (live.direction !== undefined && live.channel_address !== undefined) {
        next.direction = live.direction
        next.channel = live.channel_address
        changed = true
      }
      if (live.summary !== undefined) {
        next.summary = live.summary
        changed = true
      }
      return changed ? { ...step, event_ref: next } : step
    }
    return step
  })
}
