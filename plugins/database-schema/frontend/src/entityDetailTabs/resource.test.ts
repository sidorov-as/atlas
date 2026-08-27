import { describe, expect, it } from 'vitest'
import { resourceEntityDetailTabs } from './resource'

function entity(kind: string, capabilities: string[]) {
  return { kind, capabilities } as { kind: string; capabilities: string[] }
}

describe('resourceEntityDetailTabs', () => {
  it('shows the Schema and ER Diagram tabs for an entity declaring schema.host.v1', () => {
    const resource = entity('Resource', ['schema.host.v1'])
    for (const tab of resourceEntityDetailTabs) {
      expect(tab.when(resource)).toBe(true)
    }
  })

  it('hides both tabs when the entity does not declare the capability', () => {
    const resource = entity('Resource', [])
    for (const tab of resourceEntityDetailTabs) {
      expect(tab.when(resource)).toBe(false)
    }
  })

  it('is not scoped to a hard-coded kind check — any capability-declaring kind qualifies', () => {
    const cache = entity('Cache', ['schema.host.v1'])
    for (const tab of resourceEntityDetailTabs) {
      expect(tab.when(cache)).toBe(true)
    }
  })
})
