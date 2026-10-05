import { afterEach, describe, expect, it, vi } from 'vitest'
import { TAG_PALETTE } from 'frontend/lib/types'
import {
  defaultGraphGrouping,
  groupColorKey,
  readGraphGrouping,
  resolveGraphGrouping,
  writeGraphGrouping,
} from './graphGrouping'

function stubStorage(storage: Partial<Storage> | undefined) {
  vi.stubGlobal('window', { localStorage: storage })
}

describe('default grouping rule', () => {
  it('groups by Team from 10 Services and not below', () => {
    expect(defaultGraphGrouping(9)).toBe('none')
    expect(defaultGraphGrouping(10)).toBe('team')
    expect(defaultGraphGrouping(60)).toBe('team')
  })
})

describe('graph grouping preference', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('reads back a stored choice, including an explicit none', () => {
    const store = new Map<string, string>()
    stubStorage({ getItem: (key) => store.get(key) ?? null, setItem: (key, value) => { store.set(key, value) } })

    writeGraphGrouping('system')
    expect(readGraphGrouping()).toBe('system')
    writeGraphGrouping('none')
    expect(readGraphGrouping()).toBe('none')
    expect(store.get('atlas.apis.graphGroupBy')).toBe('none')
  })

  it('an explicit none beats the default rule above the threshold', () => {
    stubStorage({ getItem: () => 'none' })
    expect(resolveGraphGrouping(60)).toBe('none')
  })

  it('applies the default rule when nothing or an unknown value is stored', () => {
    stubStorage({ getItem: () => null })
    expect(readGraphGrouping()).toBeNull()
    expect(resolveGraphGrouping(12)).toBe('team')
    stubStorage({ getItem: () => 'tag' })
    expect(readGraphGrouping()).toBeNull()
    expect(resolveGraphGrouping(3)).toBe('none')
  })

  it('applies the default rule and does not throw when storage is unavailable', () => {
    stubStorage({ getItem: () => { throw new Error('blocked') }, setItem: () => { throw new Error('blocked') } })
    expect(resolveGraphGrouping(12)).toBe('team')
    expect(() => writeGraphGrouping('team')).not.toThrow()
    stubStorage(undefined)
    expect(resolveGraphGrouping(3)).toBe('none')
    expect(() => writeGraphGrouping('team')).not.toThrow()
  })
})

describe('groupColorKey', () => {
  it('is deterministic and always a palette color', () => {
    const ids = ['0b6f8c2e-1a2b-4c3d-8e9f-000000000001', '0b6f8c2e-1a2b-4c3d-8e9f-000000000002', 'x', '']
    for (const id of ids) {
      expect(groupColorKey(id)).toBe(groupColorKey(id))
      expect(TAG_PALETTE).toContain(groupColorKey(id))
    }
  })

  it('spreads different ids over more than one color', () => {
    const colors = new Set(Array.from({ length: 40 }, (_, index) => groupColorKey(`team-${index}`)))
    expect(colors.size).toBeGreaterThan(3)
  })
})
