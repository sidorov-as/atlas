import { describe, expect, it } from 'vitest'
import { entitySupports } from './builders'

describe('entitySupports', () => {
  it('matches an entity whose capabilities include the target capability', () => {
    const predicate = entitySupports('architecture.subject.v1')

    expect(predicate({ capabilities: ['architecture.subject.v1'] })).toBe(true)
  })

  it('does not match an entity without the target capability', () => {
    const predicate = entitySupports('architecture.subject.v1')

    expect(predicate({ capabilities: ['architecture.actor.v1'] })).toBe(false)
  })

  it('does not match an entity with no capabilities field', () => {
    const predicate = entitySupports('architecture.subject.v1')

    expect(predicate({})).toBe(false)
  })
})
