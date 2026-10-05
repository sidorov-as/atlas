import { describe, expect, it } from 'vitest'
import { allocateMembers, groupIdOf, resolveGroups } from './groupedGraph'
import { makeServiceSummary } from '../testFixtures'

const plainOf = (id: string, group: string | null) => ({ id, group })
const groupOf = (item: { group: string | null }) => item.group

describe('groupIdOf', () => {
  it('reads the team or the system and is null for a Service without one', () => {
    const service = makeServiceSummary({ teamId: 't-1', systemId: 's-1' })
    expect(groupIdOf(service, 'team')).toBe('t-1')
    expect(groupIdOf(service, 'system')).toBe('s-1')
    expect(groupIdOf(makeServiceSummary({ systemId: null }), 'system')).toBeNull()
  })
})

describe('resolveGroups', () => {
  const base = {
    groups: [{ id: 'a', name: 'A', count: 5 }, { id: 'b', name: 'B', count: 3 }, { id: 'c', name: 'C', count: 2 }],
    plain: [plainOf('p1', null), plainOf('p2', 'z')],
  }

  it('returns the unsearched structure untouched without a search', () => {
    const { groups, plain } = resolveGroups(base, null, groupOf)
    expect(groups.map((group) => [group.id, group.count, group.total, group.dimmed])).toEqual([
      ['a', 5, undefined, false], ['b', 3, undefined, false], ['c', 2, undefined, false],
    ])
    expect(plain).toBe(base.plain)
  })

  it('counts matches per group, folds a single match from the plain list and dims groups without a match', () => {
    const searched = { groups: [{ id: 'a', name: 'A', count: 2 }], plain: [plainOf('m1', 'b'), plainOf('m2', null), plainOf('m3', 'z')] }
    const { groups, plain } = resolveGroups(base, searched, groupOf)

    expect(groups.map((group) => [group.id, group.count, group.total, group.dimmed])).toEqual([
      ['a', 2, 5, false], ['b', 1, 3, false], ['c', 0, 2, true],
    ])
    // m1 is inside group b; only the genuinely ungrouped matches stay as plain nodes.
    expect(plain.map((item) => item.id)).toEqual(['m2', 'm3'])
  })
})

describe('allocateMembers', () => {
  it('shares the budget in order and reports what each group has beyond its drawn members', () => {
    const result = allocateMembers(
      [{ key: 'a', members: [1, 2, 3, 4], total: 70 }, { key: 'b', members: [5, 6], total: 2 }, { key: 'c', members: [7], total: 9 }],
      5,
    )
    expect(result.get('a')).toEqual({ drawn: [1, 2, 3, 4], more: 66 })
    expect(result.get('b')).toEqual({ drawn: [5], more: 1 })
    expect(result.get('c')).toEqual({ drawn: [], more: 9 })
  })

  it('draws nothing when the budget is spent', () => {
    expect(allocateMembers([{ key: 'a', members: [1], total: 1 }], -3).get('a')).toEqual({ drawn: [], more: 1 })
  })
})
