import { describe, expect, it } from 'vitest'
import { addConnectedStep, addTransition, canUseTransition, nextFlowStepId, parseFlowSteps, refreshStepRef, removeTransition, serializeFlowSteps, updateTransitionLabel, validateFlowSteps } from './flowSteps'
import { FLOW_LAYER_GAP, FLOW_NODE_WIDTH } from '../lib/flowLayout'
describe('Flow step utilities', () => {
  it('parses and serializes valid linear and branched steps', () => { const result = parseFlowSteps('[{"id":"start","next_steps":[{"id":"yes","label":"yes"},{"id":"no"}]},{"id":"yes"},{"id":"no"}]'); expect(result.error).toBeNull(); expect(result.steps).toHaveLength(3); expect(serializeFlowSteps(result.steps!)).toContain('"label": "yes"'); expect(validateFlowSteps(result.steps!)).toEqual([]); expect(nextFlowStepId(result.steps!)).toBe('step-4') })
  it.each([[[{ id: 'a' }, { id: 'a' }], 'Duplicate step id'], [[{ id: 'a', next_step: { id: 'missing' } }], 'unknown step id'], [[{ id: 'a', next_step: { id: 'b' } }, { id: 'b', next_step: { id: 'a' } }], 'cycle'], [[{ id: 'a', next_step: { id: 'a' } }], 'cycle']])('reports %s', (steps, expected) => expect(validateFlowSteps(steps)).toEqual(expect.arrayContaining([expect.stringContaining(expected)])))
  it('allows two steps to reconverge on the same target', () => {
    const steps = [{ id: 'a', next_steps: [{ id: 'c' }, { id: 'b' }] }, { id: 'b', next_step: { id: 'c' } }, { id: 'c' }]
    expect(validateFlowSteps(steps)).toEqual([])
  })
  it('keeps malformed or unsupported JSON out of visual mode', () => { expect(parseFlowSteps('{').error).toBeTruthy(); expect(parseFlowSteps('[{"id":"a","future":true}]').error).toContain('unsupported fields') })

  it('round-trips position, label_theme, and external_label through JSON', () => {
    const result = parseFlowSteps('[{"id":"a","position":{"x":10,"y":20},"label_theme":"danger"},{"id":"b","external_label":"Payment Gateway"}]')
    expect(result.error).toBeNull()
    expect(result.steps).toEqual([
      { id: 'a', position: { x: 10, y: 20 }, label_theme: 'danger' },
      { id: 'b', external_label: 'Payment Gateway' },
    ])
    expect(serializeFlowSteps(result.steps!)).toContain('"x": 10')
  })

  it('accepts color and icon alongside deprecated label_theme', () => {
    const result = parseFlowSteps('[{"id":"a","color":"success","icon":"Flag"},{"id":"b","label_theme":"danger"}]')
    expect(result.error).toBeNull()
    expect(result.steps).toEqual([
      { id: 'a', color: 'success', icon: 'Flag' },
      { id: 'b', label_theme: 'danger' },
    ])
  })

  it('round-trips type_label through JSON', () => {
    const result = parseFlowSteps('[{"id":"a","color":"success","icon":"Flag","type_label":"Retry"}]')
    expect(result.error).toBeNull()
    expect(result.steps).toEqual([
      { id: 'a', color: 'success', icon: 'Flag', type_label: 'Retry' },
    ])
    expect(serializeFlowSteps(result.steps!)).toContain('"type_label": "Retry"')
  })

  it.each([
    ['[{"id":"a","position":{"x":"10","y":20}}]', 'position must be'],
    ['[{"id":"a","position":{"x":10}}]', 'position must be'],
    ['[{"id":"a","label_theme":"lively"}]', 'invalid label_theme'],
    ['[{"id":"a","color":"lively"}]', 'invalid color'],
    ['[{"id":"a","icon":"NotARealIcon"}]', 'invalid icon'],
    ['[{"id":"a","external_label":"Gateway","entity_ref":"component:checkout"}]', 'cannot have more than one of entity_ref, external_label, query_ref, event_ref'],
    ['[{"id":"a","query_ref":{"api":"api:orders-api","endpoint":"e1","method":"GET"}}]', 'query_ref must have non-empty string fields'],
    ['[{"id":"a","event_ref":{"api":"api:orders-api","operation":"o1","direction":"send","channel":""}}]', 'event_ref must have non-empty string fields'],
    ['[{"id":"a","query_ref":{"api":"api:orders-api","endpoint":"e1","method":"GET","path":"/x"},"event_ref":{"api":"api:orders-api","operation":"o1","direction":"send","channel":"c"}}]', 'cannot have more than one of entity_ref, external_label, query_ref, event_ref'],
    ['[{"id":"a","entity_ref":"component:checkout","title":"Checkout"}]', 'entity_ref/query_ref/event_ref/flow_ref and cannot also have a title or summary'],
    ['[{"id":"a","entity_ref":"component:checkout","summary":"Handles checkout"}]', 'entity_ref/query_ref/event_ref/flow_ref and cannot also have a title or summary'],
    ['[{"id":"a","query_ref":{"api":"api:orders-api","endpoint":"e1","method":"GET","path":"/x"},"title":"Fetch order"}]', 'entity_ref/query_ref/event_ref/flow_ref and cannot also have a title or summary'],
    ['[{"id":"a","event_ref":{"api":"api:orders-api","operation":"o1","direction":"send","channel":"c"},"summary":"Emits the order"}]', 'entity_ref/query_ref/event_ref/flow_ref and cannot also have a title or summary'],
  ])('rejects invalid shape %s', (json, expected) => {
    expect(parseFlowSteps(json).error).toContain(expected)
  })

  it('accepts entity_ref alone, with no title or summary', () => {
    const result = parseFlowSteps('[{"id":"a","entity_ref":"component:checkout"}]')
    expect(result.error).toBeNull()
    expect(result.steps).toEqual([{ id: 'a', entity_ref: 'component:checkout' }])
  })

  it('still accepts title/summary for a Step (no entity_ref)', () => {
    const result = parseFlowSteps('[{"id":"a","title":"Retry","summary":"Retries the charge"}]')
    expect(result.error).toBeNull()
    expect(result.steps).toEqual([{ id: 'a', title: 'Retry', summary: 'Retries the charge' }])
  })

  it('accepts an optional summary on query_ref/event_ref, feeding the Call/Event card subtitle', () => {
    const result = parseFlowSteps(
      '[{"id":"a","query_ref":{"api":"api:orders-api","endpoint":"e1","method":"GET","path":"/orders","summary":"List orders"}},'
      + '{"id":"b","event_ref":{"api":"api:orders-api","operation":"o1","direction":"send","channel":"orders.created","summary":"Order created"}}]',
    )
    expect(result.error).toBeNull()
    expect(result.steps).toEqual([
      { id: 'a', query_ref: { api: 'api:orders-api', endpoint: 'e1', method: 'GET', path: '/orders', summary: 'List orders' } },
      { id: 'b', event_ref: { api: 'api:orders-api', operation: 'o1', direction: 'send', channel: 'orders.created', summary: 'Order created' } },
    ])
  })

  it('accepts an empty-string summary on query_ref (the Endpoint\'s own summary is itself optional)', () => {
    const result = parseFlowSteps('[{"id":"a","query_ref":{"api":"api:orders-api","endpoint":"e1","method":"GET","path":"/orders","summary":""}}]')
    expect(result.error).toBeNull()
  })

  it('rejects a non-string summary on query_ref', () => {
    const result = parseFlowSteps('[{"id":"a","query_ref":{"api":"api:orders-api","endpoint":"e1","method":"GET","path":"/orders","summary":123}}]')
    expect(result.error).toContain('query_ref')
  })

  it('round-trips query_ref and event_ref through JSON', () => {
    const result = parseFlowSteps(
      '[{"id":"a","query_ref":{"api":"api:orders-api","endpoint":"e1","method":"GET","path":"/orders/{id}"}},'
      + '{"id":"b","event_ref":{"api":"api:orders-api","operation":"o1","direction":"send","channel":"orders.created"}}]',
    )
    expect(result.error).toBeNull()
    expect(result.steps).toEqual([
      { id: 'a', query_ref: { api: 'api:orders-api', endpoint: 'e1', method: 'GET', path: '/orders/{id}' } },
      { id: 'b', event_ref: { api: 'api:orders-api', operation: 'o1', direction: 'send', channel: 'orders.created' } },
    ])
    expect(validateFlowSteps(result.steps!)).toEqual([])
  })

  it('round-trips flow_ref through JSON, with no title/summary', () => {
    const result = parseFlowSteps('[{"id":"a","flow_ref":42}]')
    expect(result.error).toBeNull()
    expect(result.steps).toEqual([{ id: 'a', flow_ref: 42 }])
  })

  it('rejects a non-number flow_ref', () => {
    const result = parseFlowSteps('[{"id":"a","flow_ref":"42"}]')
    expect(result.error).toContain('flow_ref')
  })

  it('rejects a flow_ref step that also carries a title or summary', () => {
    expect(parseFlowSteps('[{"id":"a","flow_ref":42,"title":"Checkout"}]').error).toContain('flow_ref')
    expect(parseFlowSteps('[{"id":"a","flow_ref":42,"summary":"Goes to checkout"}]').error).toContain('flow_ref')
  })

  it('round-trips link_url through JSON, with an optional title and summary', () => {
    const result = parseFlowSteps('[{"id":"a","link_url":"https://example.com/runbook","title":"Runbook","summary":"What to do"}]')
    expect(result.error).toBeNull()
    expect(result.steps).toEqual([{ id: 'a', link_url: 'https://example.com/runbook', title: 'Runbook', summary: 'What to do' }])
  })

  it('rejects a link_url with a disallowed scheme', () => {
    const result = parseFlowSteps('[{"id":"a","link_url":"javascript:alert(1)"}]')
    expect(result.error).toContain('link_url')
  })

  it('rejects a link_url that is not a well-formed URL', () => {
    const result = parseFlowSteps('[{"id":"a","link_url":"not a url"}]')
    expect(result.error).toContain('link_url')
  })

  it('rejects a step carrying both flow_ref and link_url', () => {
    const result = parseFlowSteps('[{"id":"a","flow_ref":1,"link_url":"https://example.com"}]')
    expect(result.error).toContain('more than one')
  })

  it('rejects a step carrying both flow_ref and entity_ref', () => {
    const result = parseFlowSteps('[{"id":"a","flow_ref":1,"entity_ref":"component:checkout"}]')
    expect(result.error).toContain('more than one')
  })

  it('addTransition sets a bare step\'s single next_step', () => {
    const next = addTransition([{ id: 'a' }, { id: 'b' }], 'a', 'b')
    expect(next.find((step) => step.id === 'a')).toEqual({ id: 'a', next_step: { id: 'b' } })
  })
  it('addTransition promotes an existing next_step into next_steps on a second connection', () => {
    const next = addTransition([{ id: 'a', next_step: { id: 'b' } }, { id: 'b' }, { id: 'c' }], 'a', 'c')
    expect(next.find((step) => step.id === 'a')).toEqual({ id: 'a', next_step: undefined, next_steps: [{ id: 'b' }, { id: 'c' }] })
  })
  it('addTransition appends to existing next_steps', () => {
    const next = addTransition([{ id: 'a', next_steps: [{ id: 'b' }] }, { id: 'b' }, { id: 'c' }], 'a', 'c')
    expect(next.find((step) => step.id === 'a')?.next_steps).toEqual([{ id: 'b' }, { id: 'c' }])
  })
  it('addTransition is a no-op when the source already targets the same step', () => {
    const steps = [{ id: 'a', next_step: { id: 'b' } }, { id: 'b' }]
    expect(addTransition(steps, 'a', 'b')).toEqual(steps)
  })

  it.each([
    [[{ id: 'a' }, { id: 'b' }], 'a', 'missing', 'existing step'],
    [[{ id: 'a' }, { id: 'b', next_step: { id: 'a' } }], 'a', 'b', 'cycle'],
  ])('canUseTransition rejects %#', (steps, source, target, expected) => {
    expect(canUseTransition(steps, source, target)).toContain(expected)
  })
  it('canUseTransition allows a valid new connection', () => {
    expect(canUseTransition([{ id: 'a' }, { id: 'b' }], 'a', 'b')).toBeNull()
  })
  it('canUseTransition allows reconverging onto an already-targeted step', () => {
    expect(canUseTransition([{ id: 'a' }, { id: 'b', next_step: { id: 'c' } }, { id: 'c' }], 'a', 'c')).toBeNull()
  })

  it('updateTransitionLabel sets a bare next_step\'s label', () => {
    const next = updateTransitionLabel([{ id: 'a', next_step: { id: 'b' } }, { id: 'b' }], 'a', 'b', 'yes')
    expect(next.find((step) => step.id === 'a')).toEqual({ id: 'a', next_step: { id: 'b', label: 'yes' } })
  })
  it('updateTransitionLabel updates the matching next_steps[] entry only', () => {
    const next = updateTransitionLabel([{ id: 'a', next_steps: [{ id: 'b' }, { id: 'c', label: 'old' }] }, { id: 'b' }, { id: 'c' }], 'a', 'c', 'new')
    expect(next.find((step) => step.id === 'a')?.next_steps).toEqual([{ id: 'b' }, { id: 'c', label: 'new' }])
  })
  it('updateTransitionLabel clears the label when given a blank string', () => {
    const next = updateTransitionLabel([{ id: 'a', next_step: { id: 'b', label: 'yes' } }, { id: 'b' }], 'a', 'b', '  ')
    expect(next.find((step) => step.id === 'a')).toEqual({ id: 'a', next_step: { id: 'b', label: undefined } })
  })

  it('addConnectedStep sets next_step and stores the given position', () => {
    const position = { x: 100 + FLOW_NODE_WIDTH + FLOW_LAYER_GAP, y: 40 }
    const next = addConnectedStep([{ id: 'a' }], 'a', { id: 'b' }, position)
    expect(next.find((step) => step.id === 'a')).toEqual({ id: 'a', next_step: { id: 'b' } })
    expect(next.find((step) => step.id === 'b')).toEqual({ id: 'b', position })
  })
  it('addConnectedStep appends a branch when the source already has a next_step', () => {
    const next = addConnectedStep([{ id: 'a', next_step: { id: 'b' } }, { id: 'b' }], 'a', { id: 'c' }, { x: 0, y: 0 })
    expect(next.find((step) => step.id === 'a')).toEqual({ id: 'a', next_step: undefined, next_steps: [{ id: 'b' }, { id: 'c' }] })
  })
  it('addConnectedStep appends to an existing next_steps branch', () => {
    const next = addConnectedStep([{ id: 'a', next_steps: [{ id: 'b' }] }, { id: 'b' }], 'a', { id: 'c' }, { x: 0, y: 0 })
    expect(next.find((step) => step.id === 'a')?.next_steps).toEqual([{ id: 'b' }, { id: 'c' }])
  })

  it('removeTransition clears a bare next_step without touching either endpoint step', () => {
    const next = removeTransition([{ id: 'a', next_step: { id: 'b' } }, { id: 'b' }], 'a', 'b')
    expect(next).toEqual([{ id: 'a', next_step: undefined }, { id: 'b' }])
  })
  it('removeTransition removes only the matching next_steps[] entry', () => {
    const next = removeTransition([{ id: 'a', next_steps: [{ id: 'b' }, { id: 'c' }] }, { id: 'b' }, { id: 'c' }], 'a', 'b')
    expect(next.find((step) => step.id === 'a')?.next_steps).toEqual([{ id: 'c' }])
  })

  it('refreshStepRef applies a query_ref\'s live summary', () => {
    const steps = [{ id: 'a', query_ref: { api: 'api:a', endpoint: 'e', method: 'GET', path: '/foo', summary: 'Old' } }]
    const next = refreshStepRef(steps, 'a', { summary: 'New' })
    expect(next.find((step) => step.id === 'a')?.query_ref).toEqual({ api: 'api:a', endpoint: 'e', method: 'GET', path: '/foo', summary: 'New' })
  })

  it('refreshStepRef applies an event_ref\'s live direction+channel as a pair', () => {
    const steps = [{ id: 'a', event_ref: { api: 'api:a', operation: 'o', direction: 'send', channel: 'orders.created' } }]
    const next = refreshStepRef(steps, 'a', { direction: 'receive', channel_address: 'orders.events' })
    expect(next.find((step) => step.id === 'a')?.event_ref).toEqual({ api: 'api:a', operation: 'o', direction: 'receive', channel: 'orders.events' })
  })

  it('refreshStepRef applies an event_ref\'s live summary independent of direction/channel', () => {
    const steps = [{ id: 'a', event_ref: { api: 'api:a', operation: 'o', direction: 'send', channel: 'orders.created', summary: 'Old' } }]
    const next = refreshStepRef(steps, 'a', { summary: 'New' })
    expect(next.find((step) => step.id === 'a')?.event_ref).toEqual({ api: 'api:a', operation: 'o', direction: 'send', channel: 'orders.created', summary: 'New' })
  })

  it('refreshStepRef applies both direction/channel and summary together when both are on live', () => {
    const steps = [{ id: 'a', event_ref: { api: 'api:a', operation: 'o', direction: 'send', channel: 'orders.created', summary: 'Old' } }]
    const next = refreshStepRef(steps, 'a', { direction: 'receive', channel_address: 'orders.events', summary: 'New' })
    expect(next.find((step) => step.id === 'a')?.event_ref).toEqual({ api: 'api:a', operation: 'o', direction: 'receive', channel: 'orders.events', summary: 'New' })
  })

  it('refreshStepRef is a no-op when live is undefined', () => {
    const steps = [{ id: 'a', query_ref: { api: 'api:a', endpoint: 'e', method: 'GET', path: '/foo', summary: 'Old' } }]
    expect(refreshStepRef(steps, 'a', undefined)).toBe(steps)
  })

  it('refreshStepRef is a no-op for a step with neither query_ref nor event_ref', () => {
    const steps = [{ id: 'a', entity_ref: 'component:checkout' }]
    const next = refreshStepRef(steps, 'a', { summary: 'New' })
    expect(next.find((step) => step.id === 'a')).toEqual({ id: 'a', entity_ref: 'component:checkout' })
  })
})
