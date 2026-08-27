// @vitest-environment jsdom
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { ThemeProvider } from '@gravity-ui/uikit'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { groupsApi } from 'frontend/lib/entities'
import { TeamsListPage } from './TeamsListPage'

afterEach(() => cleanup())

class ResizeObserverStub { observe() {} unobserve() {} disconnect() {} }
globalThis.ResizeObserver = ResizeObserverStub

window.matchMedia = window.matchMedia || (((query: string) => ({
  matches: false,
  media: query,
  onchange: null,
  addListener: () => {},
  removeListener: () => {},
  addEventListener: () => {},
  removeEventListener: () => {},
  dispatchEvent: () => false,
})) as unknown as typeof window.matchMedia)

vi.mock('frontend/lib/entities', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/entities')>()
  return { ...actual, groupsApi: { ...actual.groupsApi, list: vi.fn() } }
})

describe('TeamsListPage', () => {
  it('keeps its page heading above a table-aligned preview row', async () => {
    vi.mocked(groupsApi.list).mockResolvedValue({
      count: 1,
      numPages: 1,
      perPage: 20,
      page: { number: 1, objectList: [{
        id: 1,
        apiVersion: 'atlas/v1alpha1',
        kind: 'Group',
        metadata: { name: 'platform', title: 'Platform', description: '', documentation: '', labels: {}, tags: [], tagColors: {}, links: [] },
        spec: { type: 'team', members: [] },
        capabilities: [],
      }] },
    })
    const { container } = render(<ThemeProvider theme="light"><MemoryRouter><TeamsListPage /></MemoryRouter></ThemeProvider>)

    await waitFor(() => expect(screen.getByText('Platform')).toBeDefined())
    const root = container.firstElementChild
    const contentRow = root?.lastElementChild as HTMLElement
    expect(root?.firstElementChild?.textContent).toContain('Teams')
    expect(contentRow.style.display).toBe('flex')
    expect((contentRow.firstElementChild as HTMLElement).style.maxWidth).toBe('min(1440px, 100%)')
  })
})
