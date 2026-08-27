// @vitest-environment jsdom
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { ThemeProvider } from '@gravity-ui/uikit'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { SettingsLayout } from './SettingsLayout'
import { catalogHomeSettingsApi, tagsApi } from '../lib/entities'
import { useSession } from '../lib/SessionContext'
import type { SessionState } from '../lib/auth'

afterEach(() => cleanup())

// jsdom has no ResizeObserver; Gravity UI's Table (used by SettingsTagsPage) needs one to mount.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
vi.stubGlobal('ResizeObserver', ResizeObserverStub)

vi.mock('../lib/entities', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../lib/entities')>()),
  catalogHomeSettingsApi: { get: vi.fn(), update: vi.fn() },
  tagsApi: { list: vi.fn(), updateColor: vi.fn() },
}))

vi.mock('../lib/SessionContext', () => ({
  useSession: vi.fn(),
}))

function mockSession(session: SessionState) {
  vi.mocked(useSession).mockReturnValue({
    session,
    isLoading: false,
    error: false,
    login: vi.fn(),
    logout: vi.fn(),
    refresh: vi.fn(),
  })
}

const HOME_SECTION_TEXT = 'Edit the "About this catalog" section shown on the homepage'
const TAGS_SECTION_TEXT = 'Configure the color used to render each tag across the catalog'

function renderAt(path: string) {
  vi.mocked(catalogHomeSettingsApi.get).mockResolvedValue({ aboutMarkdown: 'hello' })
  vi.mocked(tagsApi.list).mockResolvedValue([{ id: 1, name: 'billing', color: 'blue' }])
  return render(
    <ThemeProvider theme="light">
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/settings/*" element={<SettingsLayout />} />
        </Routes>
      </MemoryRouter>
    </ThemeProvider>,
  )
}

describe('SettingsLayout', () => {
  beforeEach(() => mockSession({ isAuthenticated: true, user: null, isAdmin: true, isReadOnly: false }))

  it('shows a sub-nav item for every section', () => {
    renderAt('/settings/home')
    expect(screen.getAllByText('Home').length).toBeGreaterThan(0)
    expect(screen.getByText('Tag colors')).toBeDefined()
  })

  it('redirects the bare Settings URL to the Home section', async () => {
    renderAt('/settings')
    await waitFor(() => expect(screen.getByText(HOME_SECTION_TEXT)).toBeDefined())
  })

  it('renders the Home section directly at /settings/home', async () => {
    renderAt('/settings/home')
    await waitFor(() => expect(screen.getByText(HOME_SECTION_TEXT)).toBeDefined())
    expect(screen.queryByText(TAGS_SECTION_TEXT)).toBeNull()
  })

  it('renders the Tag colors section directly at /settings/tags, without the Home section', async () => {
    renderAt('/settings/tags')
    await waitFor(() => expect(screen.getByText(TAGS_SECTION_TEXT)).toBeDefined())
    expect(screen.queryByText(HOME_SECTION_TEXT)).toBeNull()
  })

  it('hides the Home Save control for a read-only admin (catalog-web-ui spec)', async () => {
    mockSession({ isAuthenticated: true, user: null, isAdmin: true, isReadOnly: true })
    renderAt('/settings/home')
    await waitFor(() => expect(screen.getByText(HOME_SECTION_TEXT)).toBeDefined())
    expect(screen.queryByRole('button', { name: 'Save' })).toBeNull()
  })

  it('hides the tag color editor/Save for a read-only admin (catalog-web-ui spec)', async () => {
    mockSession({ isAuthenticated: true, user: null, isAdmin: true, isReadOnly: true })
    renderAt('/settings/tags')
    await waitFor(() => expect(screen.getAllByText('billing').length).toBeGreaterThan(0))
    expect(screen.queryByRole('button', { name: 'Save' })).toBeNull()
  })
})
