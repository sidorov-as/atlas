// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { ThemeProvider } from '@gravity-ui/uikit'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { FlowDetailPage } from './FlowDetailPage'
import { flowsApi } from 'frontend/lib/entities'
import { useSession } from 'frontend/lib/SessionContext'

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

class ResizeObserverStub { observe() {} unobserve() {} disconnect() {} }
vi.stubGlobal('ResizeObserver', ResizeObserverStub)
vi.stubGlobal('matchMedia', (query: string) => ({
  matches: false, media: query, onchange: null,
  addListener: () => {}, removeListener: () => {},
  addEventListener: () => {}, removeEventListener: () => {}, dispatchEvent: () => false,
}))

vi.mock('../components/FlowGraph', () => ({ FlowGraph: () => <div>Graph</div> }))
vi.mock('frontend/components/DocumentationPreview', () => ({
  DocumentationPreview: ({ value }: { value: string }) => <div>{value}</div>,
}))
vi.mock('frontend/lib/entities', () => ({
  flowsApi: { get: vi.fn(), remove: vi.fn() },
}))
vi.mock('frontend/lib/SessionContext', () => ({
  useSession: vi.fn(),
}))

function mockSession(isReadOnly: boolean) {
  vi.mocked(useSession).mockReturnValue({
    session: { isAuthenticated: true, user: null, isAdmin: false, isReadOnly },
    isLoading: false,
    error: false,
    login: vi.fn(),
    logout: vi.fn(),
    refresh: vi.fn(),
  })
}

function renderFlowDetailPage(initialEntry = '/flows/1', permissions?: { canEdit: boolean }) {
  vi.mocked(flowsApi.get).mockResolvedValue({
    id: 1,
    system: 'system:payments',
    name: 'checkout',
    description: 'Short summary',
    documentation: '## Operational notes\n\nWatch the queue.',
    steps: [{ id: 'start', title: 'Start' }],
    ...(permissions ? { permissions } : {}),
  })
  return render(
    <ThemeProvider theme="light">
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes><Route path="/flows/:id" element={<FlowDetailPage />} /></Routes>
      </MemoryRouter>
    </ThemeProvider>,
  )
}

describe('FlowDetailPage', () => {
  beforeEach(() => mockSession(false))

  it('defaults to the Overview tab, showing documentation', async () => {
    renderFlowDetailPage()

    await waitFor(() => expect(screen.getByText(/Operational notes/)).toBeDefined())
    expect(screen.getByRole('tab', { name: 'Overview' })).toBeDefined()
    expect(screen.getByRole('tab', { name: 'Flow' })).toBeDefined()
  })

  it('shows the flow graph on the Flow tab', async () => {
    renderFlowDetailPage()

    await waitFor(() => expect(screen.getByText(/Operational notes/)).toBeDefined())
    fireEvent.click(screen.getByRole('tab', { name: 'Flow' }))
    await waitFor(() => expect(screen.getByText('Graph')).toBeDefined())
  })

  it('opens straight on the Flow tab when the URL carries ?tab=flow (a Flow node\'s navigate control)', async () => {
    renderFlowDetailPage('/flows/1?tab=flow')

    await waitFor(() => expect(screen.getByText('Graph')).toBeDefined())
    expect(screen.queryByText(/Operational notes/)).toBeNull()
  })

  it('deletes the flow via a danger-styled confirm dialog, not a native confirm', async () => {
    vi.mocked(flowsApi.remove).mockResolvedValue(undefined)
    renderFlowDetailPage()

    await waitFor(() => expect(screen.getByText(/Operational notes/)).toBeDefined())
    fireEvent.click(screen.getByRole('button', { name: 'Delete' }))

    await waitFor(() => expect(screen.getByText(/cannot be undone/i)).toBeDefined())
    const applyButton = screen.getByText('Confirm').closest('button')
    expect(applyButton?.className).toMatch(/preset_danger/)

    fireEvent.click(screen.getByText('Confirm'))
    await waitFor(() => expect(flowsApi.remove).toHaveBeenCalledWith(1))
  })

  it('does not delete the flow when the confirm dialog is cancelled', async () => {
    renderFlowDetailPage()

    await waitFor(() => expect(screen.getByText(/Operational notes/)).toBeDefined())
    fireEvent.click(screen.getByRole('button', { name: 'Delete' }))

    await waitFor(() => expect(screen.getByText(/cannot be undone/i)).toBeDefined())
    fireEvent.click(screen.getByText('Cancel'))

    await waitFor(() => expect(screen.queryByText(/cannot be undone/i)).toBeNull())
    expect(flowsApi.remove).not.toHaveBeenCalled()
  })

  it('hides Edit and Delete for a read-only session', async () => {
    mockSession(true)
    renderFlowDetailPage()

    await waitFor(() => expect(screen.getByText(/Operational notes/)).toBeDefined())
    expect(screen.queryByRole('button', { name: 'Edit' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Delete' })).toBeNull()
  })

  it('hides Edit and Delete when the server says the user may not edit the flow', async () => {
    renderFlowDetailPage('/flows/1', { canEdit: false })

    await waitFor(() => expect(screen.getByText(/Operational notes/)).toBeDefined())
    expect(screen.queryByRole('button', { name: 'Edit' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Delete' })).toBeNull()
  })

  it('shows Edit and Delete when the server grants edit permission', async () => {
    renderFlowDetailPage('/flows/1', { canEdit: true })

    await waitFor(() => expect(screen.getByRole('button', { name: 'Edit' })).toBeDefined())
    expect(screen.getByRole('button', { name: 'Delete' })).toBeDefined()
  })
})
