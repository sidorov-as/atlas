import { describe, expect, it } from 'vitest'
import { FLOW_NODE_KIND_LABELS, flowNodeKindOf, stepTypeLabel } from './flowNodeKind'

describe('flowNodeKindOf', () => {
  it('derives flow for a step with flow_ref', () => {
    expect(flowNodeKindOf({ id: 'a', flow_ref: 42 })).toBe('flow')
  })

  it('derives link for a step with link_url', () => {
    expect(flowNodeKindOf({ id: 'a', link_url: 'https://example.com' })).toBe('link')
  })

  it('still derives call/event/entity kinds ahead of flow/link (none set together, but checked first)', () => {
    expect(flowNodeKindOf({ id: 'a', query_ref: { api: 'api:orders-api', endpoint: 'e1', method: 'GET', path: '/x' } })).toBe('call')
    expect(flowNodeKindOf({ id: 'a', entity_ref: 'component:checkout' })).toBe('component')
  })

  it('falls back to external, then step, when neither flow_ref nor link_url is set', () => {
    expect(flowNodeKindOf({ id: 'a', external_label: 'Gateway' })).toBe('external')
    expect(flowNodeKindOf({ id: 'a' })).toBe('step')
  })
})

describe('stepTypeLabel', () => {
  it('returns the chosen type_label when set', () => {
    expect(stepTypeLabel({ type_label: 'Retry' })).toBe('Retry')
  })

  it('falls back to "Step" when type_label is blank/whitespace-only', () => {
    expect(stepTypeLabel({ type_label: '   ' })).toBe(FLOW_NODE_KIND_LABELS.step)
  })

  it('falls back to "Step" when type_label is unset', () => {
    expect(stepTypeLabel({})).toBe(FLOW_NODE_KIND_LABELS.step)
  })
})
