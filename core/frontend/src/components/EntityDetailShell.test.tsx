// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ThemeProvider } from '@gravity-ui/uikit'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { EntityDetailShell } from './EntityDetailShell'
import { entityDetailTab } from '@atlas/plugin-api'
import { useSession } from '../lib/SessionContext'
import type { SessionState } from '../lib/auth'
import type { SystemEntity } from '../lib/types'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

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

const NOT_READ_ONLY: SessionState = { isAuthenticated: true, user: null, isAdmin: false, isReadOnly: false }

class ResizeObserverStub { observe() {} unobserve() {} disconnect() {} }
globalThis.ResizeObserver = globalThis.ResizeObserver ?? ResizeObserverStub

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

const metadata = { name: 'portal', title: '', description: '', documentation: '', labels: {}, tags: [], tagColors: {}, links: [] }

function makeSystem(overrides: Partial<SystemEntity> = {}): SystemEntity {
  return {
    id: 'system-1',
    apiVersion: 'atlas/v1alpha1',
    kind: 'System',
    metadata,
    spec: { owner: 'group:platform', ownerId: 'group-1' },
    status: 'active',
    ingestedFrom: null,
    blockedBy: null,
    blockedByReason: null,
    capabilities: ['architecture.subject.v1'],
    ...overrides,
  }
}

function renderShell(
  entity: SystemEntity,
  tabContributions: Parameters<typeof EntityDetailShell>[0]['tabContributions'],
  overrides: Partial<Parameters<typeof EntityDetailShell>[0]> = {},
) {
  return render(
    <ThemeProvider theme="light">
      <MemoryRouter>
        <EntityDetailShell
          breadcrumb={{ label: 'Systems', to: '/systems' }}
          metadata={entity.metadata}
          ingestedFrom={entity.ingestedFrom}
          isLoading={false}
          error={null}
          editTo="/systems/1/edit"
          railFields={[{ label: 'Owner', value: 'Platform' }]}
          entity={entity}
          tabContributions={tabContributions}
          {...overrides}
        />
      </MemoryRouter>
    </ThemeProvider>,
  )
}

function renderUnavailableShell(tabContributions: Parameters<typeof EntityDetailShell>[0]['tabContributions']) {
  return render(
    <ThemeProvider theme="light">
      <MemoryRouter>
        <EntityDetailShell
          breadcrumb={{ label: 'Systems', to: '/systems' }}
          metadata={metadata}
          ingestedFrom={null}
          isLoading={false}
          error={null}
          editTo="/systems/1/edit"
          unavailable
          railFields={[]}
          entity={undefined}
          tabContributions={tabContributions}
        />
      </MemoryRouter>
    </ThemeProvider>,
  )
}

describe('EntityDetailShell', () => {
  beforeEach(() => mockSession(NOT_READ_ONLY))

  it('only renders tabs whose contribution `when` matches the entity', () => {
    renderShell(makeSystem(), [
      entityDetailTab({ id: 'a', value: 'overview', label: 'Overview', when: () => true, component: () => <div>Overview content</div> }),
      entityDetailTab({ id: 'b', value: 'other-kind', label: 'Other Kind Only', when: () => false, component: () => <div /> }),
    ])
    expect(screen.getByRole('tab', { name: 'Overview' })).toBeDefined()
    expect(screen.queryByRole('tab', { name: 'Other Kind Only' })).toBeNull()
  })

  it('shows a link type label next to the link in the aside rail', () => {
    renderShell(makeSystem(), [], {
      links: [{ title: 'Runbook', description: '', url: 'https://example.test/runbook', type: 'runbook' }],
    })

    const link = screen.getByRole('link', { name: 'Runbook' })
    expect(link.getAttribute('href')).toBe('https://example.test/runbook')
    expect(screen.getByText('runbook')).toBeDefined()
  })

  it('uses full page width for a full-width tab while ordinary tabs retain the right rail', async () => {
    renderShell(makeSystem(), [
      entityDetailTab({ id: 'a', value: 'overview', label: 'Overview', when: () => true, component: () => <div>Overview content</div> }),
      entityDetailTab({ id: 'b', value: 'diagram', label: 'Diagram', fullWidth: true, when: () => true, component: () => <div>Diagram content</div> }),
    ])
    expect(screen.getByText('About')).toBeDefined()
    fireEvent.click(screen.getByRole('tab', { name: 'Diagram' }))
    await waitFor(() => expect(screen.getByText('Diagram content')).toBeDefined())
    await waitFor(() => expect(screen.queryByText('About')).toBeNull())
  })

  it('isolates a failing tab so the rest of the page, including its other tabs, stays usable', async () => {
    function BrokenTab(): never {
      throw new Error('boom')
    }
    renderShell(makeSystem(), [
      entityDetailTab({ id: 'a', value: 'overview', label: 'Overview', when: () => true, component: () => <div>Overview content</div> }),
      entityDetailTab({ id: 'b', value: 'broken', label: 'Broken', when: () => true, component: BrokenTab }),
    ])
    expect(screen.getByText('Overview content')).toBeDefined()
    fireEvent.click(screen.getByRole('tab', { name: 'Broken' }))
    await waitFor(() => expect(screen.getByText('Broken failed to load')).toBeDefined())
    fireEvent.click(screen.getByRole('tab', { name: 'Overview' }))
    await waitFor(() => expect(screen.getByText('Overview content')).toBeDefined())
  })

  it('renders the unavailable banner, hides Edit, and shows no kind-specific tabs when unavailable', () => {
    renderUnavailableShell([
      entityDetailTab({ id: 'a', value: 'overview', label: 'Overview', when: () => true, component: () => <div>Overview content</div> }),
    ])
    expect(screen.getByText('This entity is unavailable')).toBeDefined()
    expect(screen.queryByRole('button', { name: 'Edit' })).toBeNull()
    expect(screen.queryByRole('tab', { name: 'Overview' })).toBeNull()
    expect(screen.getAllByText('portal').length).toBeGreaterThan(0)
  })

  it('shows Remove (not Revive/Purge/Delete) for an active manual entity', () => {
    renderShell(makeSystem({ status: 'active' }), [], { onRemove: async () => {}, onRevive: async () => {}, onPurge: async () => {} })
    expect(screen.getByRole('button', { name: 'Remove' })).toBeDefined()
    expect(screen.queryByRole('button', { name: 'Revive' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Purge' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Delete' })).toBeNull()
    expect(screen.queryByText('Removed')).toBeNull()
  })

  it('shows a "Removed" badge in the header for a removed entity', () => {
    renderShell(makeSystem({ status: 'removed' }), [], { onRemove: async () => {}, onRevive: async () => {}, onPurge: async () => {} })
    expect(screen.getByText('Removed')).toBeDefined()
  })

  it('shows Revive and Purge (not Remove) for a removed manual entity', () => {
    renderShell(makeSystem({ status: 'removed' }), [], { onRemove: async () => {}, onRevive: async () => {}, onPurge: async () => {} })
    expect(screen.queryByRole('button', { name: 'Remove' })).toBeNull()
    expect(screen.getByRole('button', { name: 'Revive' })).toBeDefined()
    expect(screen.getByRole('button', { name: 'Purge' })).toBeDefined()
  })

  it('shows Purge for a removed YAML-managed entity even though Edit/Remove/Revive are hidden', () => {
    renderShell(
      makeSystem({ status: 'removed', ingestedFrom: 'org/repo' }),
      [],
      { onRemove: async () => {}, onRevive: async () => {}, onPurge: async () => {} },
    )
    expect(screen.queryByRole('button', { name: 'Edit' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Remove' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Revive' })).toBeNull()
    expect(screen.getByRole('button', { name: 'Purge' })).toBeDefined()
  })

  it('opens a revivable-phrased confirm dialog and calls onRemove once confirmed', async () => {
    const onRemove = vi.fn().mockResolvedValue(undefined)
    renderShell(makeSystem({ status: 'active' }), [], { onRemove, onRevive: async () => {}, onPurge: async () => {} })

    fireEvent.click(screen.getByRole('button', { name: 'Remove' }))
    await waitFor(() => expect(screen.getByText(/revived later/i)).toBeDefined())
    fireEvent.click(screen.getByText('Confirm'))

    await waitFor(() => expect(onRemove).toHaveBeenCalled())
  })

  it('does not call onRemove when the confirm dialog is cancelled', async () => {
    const onRemove = vi.fn().mockResolvedValue(undefined)
    renderShell(makeSystem({ status: 'active' }), [], { onRemove, onRevive: async () => {}, onPurge: async () => {} })

    fireEvent.click(screen.getByRole('button', { name: 'Remove' }))
    await waitFor(() => expect(screen.getByText(/revived later/i)).toBeDefined())
    fireEvent.click(screen.getByText('Cancel'))

    await waitFor(() => expect(screen.queryByText(/revived later/i)).toBeNull())
    expect(onRemove).not.toHaveBeenCalled()
  })

  it('opens a danger-styled Purge confirm dialog and navigates to the breadcrumb after a successful Purge', async () => {
    const onPurge = vi.fn().mockResolvedValue(undefined)
    renderShell(makeSystem({ status: 'removed' }), [], { onRemove: async () => {}, onRevive: async () => {}, onPurge })

    fireEvent.click(screen.getByRole('button', { name: 'Purge' }))
    await waitFor(() => expect(screen.getByText(/cannot be undone/i)).toBeDefined())
    const applyButton = screen.getByText('Confirm').closest('button')
    expect(applyButton?.className).toMatch(/preset_danger/)
    fireEvent.click(screen.getByText('Confirm'))

    await waitFor(() => expect(onPurge).toHaveBeenCalled())
  })

  it('hides Edit/Remove/Revive/Purge for a read-only session even when the entity is otherwise manual (catalog-web-ui spec)', () => {
    mockSession({ isAuthenticated: true, user: null, isAdmin: true, isReadOnly: true })
    renderShell(makeSystem({ status: 'active' }), [], { onRemove: async () => {}, onRevive: async () => {}, onPurge: async () => {} })
    expect(screen.queryByRole('button', { name: 'Edit' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Remove' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Revive' })).toBeNull()
  })

  it('hides Purge for a read-only session even for a removed entity', () => {
    mockSession({ isAuthenticated: true, user: null, isAdmin: false, isReadOnly: true })
    renderShell(makeSystem({ status: 'removed' }), [], { onRemove: async () => {}, onRevive: async () => {}, onPurge: async () => {} })
    expect(screen.queryByRole('button', { name: 'Purge' })).toBeNull()
  })
})
