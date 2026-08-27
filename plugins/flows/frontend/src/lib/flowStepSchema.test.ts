import { describe, expect, it } from 'vitest'
import { flowStepSchema } from './flowStepSchema'

// Regression test for a real bug: `flowStepSchema.ts` (the Monaco JSON-rail schema) is a
// separate, hand-maintained mirror of `flowSteps.ts::parseFlowSteps` and `models.py`'s shape
// checks — nothing enforces they stay in sync. Adding `query_ref`/`event_ref`'s optional
// `summary` key to the other
// two but not here made the JSON rail reject a perfectly valid, already-saved step with
// "Property summary is not allowed", even though parsing/saving it worked fine.
describe('flowStepSchema query_ref/event_ref allow the optional summary key', () => {
  function refSchemaOf(field: 'query_ref' | 'event_ref') {
    const wrapper = (flowStepSchema.items.properties as Record<string, { anyOf: [{ properties: Record<string, unknown>, required: string[] }, unknown] }>)[field]
    return wrapper.anyOf[0]
  }

  it('query_ref schema declares a string summary property, not required', () => {
    const schema = refSchemaOf('query_ref')
    expect(schema.properties.summary).toMatchObject({ type: 'string' })
    expect(schema.required).not.toContain('summary')
  })

  it('event_ref schema declares a string summary property, not required', () => {
    const schema = refSchemaOf('event_ref')
    expect(schema.properties.summary).toMatchObject({ type: 'string' })
    expect(schema.required).not.toContain('summary')
  })
})

// Same regression-prevention rationale as above, for the flow_ref/link_url fields:
// the Monaco JSON rail is a hand-maintained mirror of `flowSteps.ts`/`models.py`, so adding
// flow_ref/link_url to those without also adding them here would make the JSON rail reject
// valid Flow/Link steps.
describe('flowStepSchema declares flow_ref and link_url', () => {
  const properties = flowStepSchema.items.properties as Record<string, { type: string | string[] }>

  it('flow_ref is declared as an optional number', () => {
    expect(properties.flow_ref.type).toEqual(['number', 'null'])
  })

  it('link_url is declared as an optional string', () => {
    expect(properties.link_url.type).toEqual(['string', 'null'])
  })

  it('the mutual-exclusivity rule covers all 15 pairs among the six ref fields', () => {
    const notAnyOf = (
      flowStepSchema.items.allOf[0] as { not: { anyOf: { required: string[] }[] } }
    ).not.anyOf
    expect(notAnyOf).toHaveLength(15)
    const pairs = notAnyOf.map((entry) => [...entry.required].sort().join('+'))
    expect(pairs).toContain('flow_ref+link_url')
    expect(pairs).toContain('entity_ref+flow_ref')
    expect(pairs).toContain('external_label+link_url')
    expect(new Set(pairs).size).toBe(15)
  })
})
