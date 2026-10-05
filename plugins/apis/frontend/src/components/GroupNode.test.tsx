// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import { ThemeProvider } from '@gravity-ui/uikit'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { NodeProps } from '@xyflow/react'
import { GROUP_NODE_TYPE, GroupNode, groupCaption, type GroupFlowNode } from './GroupNode'

afterEach(cleanup)

vi.mock('@xyflow/react', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@xyflow/react')>()
  return { ...actual, Handle: () => null }
})

function renderGroup(data: Partial<GroupFlowNode['data']> = {}) {
  const props = {
    id: 'group-1',
    type: GROUP_NODE_TYPE,
    data: { groupId: 'team-1', name: 'Payments Team', count: 12, colorKey: 'blue', expanded: false, ...data },
  } as unknown as NodeProps<GroupFlowNode>
  return render(<ThemeProvider theme="light"><GroupNode {...props} /></ThemeProvider>)
}

describe('GroupNode', () => {
  it('shows the name, the size and a collapsed state', () => {
    renderGroup()
    const node = screen.getByRole('button', { name: 'Payments Team, 12 services' })
    expect(node.getAttribute('aria-expanded')).toBe('false')
    expect(node.className).toContain('tag-preset-blue')
    expect(screen.getByText('Payments Team')).toBeTruthy()
    expect(screen.getByText('12 services')).toBeTruthy()
  })

  it('reports the expanded state', () => {
    renderGroup({ expanded: true })
    expect(screen.getByRole('button').getAttribute('aria-expanded')).toBe('true')
  })

  it('reads "N of M matches" while a search is active', () => {
    renderGroup({ count: 2, total: 5 })
    expect(screen.getByText('2 of 5 matches')).toBeTruthy()
  })
})

describe('groupCaption', () => {
  it('uses the singular for one Service and the match form when searching', () => {
    expect(groupCaption({ count: 1 })).toBe('1 service')
    expect(groupCaption({ count: 0, total: 4 })).toBe('0 of 4 matches')
  })
})
