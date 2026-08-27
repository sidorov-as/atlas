// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ThemeProvider } from '@gravity-ui/uikit'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { RelationsTab } from './RelationsTab'
import { architectureRelationshipsApi } from '../lib/entities'
import { useSession } from '../lib/SessionContext'

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

class ResizeObserverStub { observe() {} unobserve() {} disconnect() {} }
globalThis.ResizeObserver = ResizeObserverStub

// jsdom has no matchMedia; Gravity UI's Popup (used by the target lookup's Select) needs it.
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

vi.mock('../lib/entities', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/entities')>()
  return {
    ...actual,
    architectureRelationshipsApi: { ...actual.architectureRelationshipsApi, create: vi.fn(), remove: vi.fn().mockResolvedValue(undefined) },
    systemsApi: { ...actual.systemsApi, list: vi.fn().mockResolvedValue({ count: 1, numPages: 1, perPage: 100, page: { number: 1, objectList: [{ metadata: { name: 'checkout', title: 'Checkout' } }] } }) },
    componentsApi: { ...actual.componentsApi, list: vi.fn().mockResolvedValue({ count: 1, numPages: 1, perPage: 100, page: { number: 1, objectList: [{ metadata: { name: 'api-gateway', title: 'API Gateway' } }] } }) },
    apisApi: { ...actual.apisApi, list: vi.fn().mockResolvedValue({ count: 1, numPages: 1, perPage: 100, page: { number: 1, objectList: [{ metadata: { name: 'orders-api', title: 'Orders API' } }] } }) },
    resourcesApi: { ...actual.resourcesApi, list: vi.fn().mockResolvedValue({ count: 1, numPages: 1, perPage: 100, page: { number: 1, objectList: [{ metadata: { name: 'orders-db', title: 'Orders DB' } }] } }) },
    usersApi: { ...actual.usersApi, list: vi.fn().mockResolvedValue([{ metadata: { name: 'jane-doe', title: 'Jane Doe' } }]) },
    groupsApi: { ...actual.groupsApi, list: vi.fn().mockResolvedValue({ count: 1, numPages: 1, perPage: 20, page: { number: 1, objectList: [{ metadata: { name: 'payments', title: 'Payments Team' } }] } }) },
  }
})

vi.mock('../lib/SessionContext', () => ({
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

const architectureRelationship = {
  id: 7,
  source: 'component:portal', sourceKind: 'component', sourceId: 'component-1',
  sourceStatus: 'active' as const, sourceDeprecated: false,
  target: 'api:gateway', targetKind: 'api', targetId: 'api-2',
  targetStatus: 'active' as const, targetDeprecated: false,
  label: 'Makes API calls to', technology: 'REST/HTTPS', interactionKind: 'synchronous' as const,
  tags: ['critical'], origin: 'yaml' as const,
}

function renderRelations(canManageArchitectureRelationships: boolean) {
  return render(
    <ThemeProvider theme="light"><MemoryRouter><RelationsTab
      source="component:portal"
      canManageArchitectureRelationships={canManageArchitectureRelationships}
      fetchRelations={async () => [{
        predicate: 'consumesAPI', target: 'api:gateway', targetKind: 'api', targetId: 'api-2',
        status: 'active' as const, deprecated: false,
      }]}
      fetchArchitectureRelationships={async () => [architectureRelationship]}
    /></MemoryRouter></ThemeProvider>,
  )
}

describe('RelationsTab', () => {
  beforeEach(() => mockSession(false))

  it('separates catalog and architecture relationships with their metadata', async () => {
    renderRelations(true)
    await waitFor(() => expect(screen.getByText('Catalog Relations')).toBeDefined())
    expect(screen.getByText('Architecture Relationships')).toBeDefined()
    expect(screen.getByText('Makes API calls to')).toBeDefined()
    expect(screen.getByText('REST/HTTPS')).toBeDefined()
    expect(screen.getByText('synchronous')).toBeDefined()
  })

  it('shows a warning badge on a catalog relation whose target was removed', async () => {
    render(
      <ThemeProvider theme="light"><MemoryRouter><RelationsTab
        source="component:portal"
        canManageArchitectureRelationships
        fetchRelations={async () => [{
          predicate: 'consumesAPI', target: 'api:gateway', targetKind: 'api', targetId: 'api-2',
          status: 'removed' as const, deprecated: false,
        }]}
        fetchArchitectureRelationships={async () => []}
      /></MemoryRouter></ThemeProvider>,
    )

    await waitFor(() => expect(screen.getByText('Catalog Relations')).toBeDefined())
    expect(screen.getByLabelText(/removed from the catalog/)).toBeDefined()
  })

  it('shows no warning badge on a catalog relation whose target is active and not deprecated', async () => {
    renderRelations(true)
    await waitFor(() => expect(screen.getByText('Catalog Relations')).toBeDefined())
    expect(screen.queryByLabelText(/removed from the catalog/)).toBeNull()
    expect(screen.queryByLabelText(/is deprecated/)).toBeNull()
  })

  it('shows a warning badge on an architecture relationship whose target is deprecated', async () => {
    render(
      <ThemeProvider theme="light"><MemoryRouter><RelationsTab
        source="component:portal"
        canManageArchitectureRelationships
        fetchRelations={async () => []}
        fetchArchitectureRelationships={async () => [{ ...architectureRelationship, targetDeprecated: true }]}
      /></MemoryRouter></ThemeProvider>,
    )

    await waitFor(() => expect(screen.getByText('Architecture Relationships')).toBeDefined())
    expect(screen.getByLabelText(/is deprecated/)).toBeDefined()
  })

  it('shows YAML-origin relationships as read-only without authoring controls', async () => {
    renderRelations(false)
    await waitFor(() => expect(screen.getByText('Read-only')).toBeDefined())
    expect(screen.getByText(/declared in YAML are read-only/i)).toBeDefined()
    expect(screen.queryByRole('button', { name: 'Add relationship' })).toBeNull()
  })

  it('shows canonical source-to-target direction and makes manual incoming relationships read-only', async () => {
    const incomingRelationship = {
      ...architectureRelationship,
      origin: 'manual' as const,
      source: 'component:checkout', sourceKind: 'component', sourceId: 'component-3',
      target: 'component:portal', targetKind: 'component', targetId: 'component-1',
    }
    render(
      <ThemeProvider theme="light"><MemoryRouter><RelationsTab
        source="component:portal"
        canManageArchitectureRelationships
        fetchRelations={async () => []}
        fetchArchitectureRelationships={async () => [incomingRelationship]}
      /></MemoryRouter></ThemeProvider>,
    )

    await waitFor(() => expect(screen.getByText('Source')).toBeDefined())
    expect(screen.getAllByText('Target')).toHaveLength(2)
    expect(screen.getByText('checkout')).toBeDefined()
    expect(screen.getByText('portal')).toBeDefined()
    expect(screen.getByText('Read-only')).toBeDefined()
    expect(screen.queryByRole('button', { name: 'Edit' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Delete' })).toBeNull()
  })

  it('keeps YAML relationships read-only even when the current entity is otherwise manageable', async () => {
    renderRelations(true)

    await waitFor(() => expect(screen.getByText('Read-only')).toBeDefined())
    expect(screen.queryByRole('button', { name: 'Edit' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Delete' })).toBeNull()
  })

  it('deletes a manual relationship via a danger-styled confirm dialog, not a native confirm', async () => {
    const manualRelationship = { ...architectureRelationship, origin: 'manual' as const, source: 'component:portal' }
    render(
      <ThemeProvider theme="light"><MemoryRouter><RelationsTab
        source="component:portal"
        canManageArchitectureRelationships
        fetchRelations={async () => []}
        fetchArchitectureRelationships={async () => [manualRelationship]}
      /></MemoryRouter></ThemeProvider>,
    )

    await waitFor(() => expect(screen.getByRole('button', { name: 'Delete' })).toBeDefined())
    fireEvent.click(screen.getByRole('button', { name: 'Delete' }))

    await waitFor(() => expect(screen.getByText(/cannot be undone/i)).toBeDefined())
    const applyButton = screen.getByText('Confirm').closest('button')
    expect(applyButton?.className).toMatch(/preset_danger/)

    fireEvent.click(screen.getByText('Confirm'))
    await waitFor(() => expect(architectureRelationshipsApi.remove).toHaveBeenCalledWith(manualRelationship.id))
  })

  it('does not delete the relationship when the confirm dialog is cancelled', async () => {
    const manualRelationship = { ...architectureRelationship, origin: 'manual' as const, source: 'component:portal' }
    render(
      <ThemeProvider theme="light"><MemoryRouter><RelationsTab
        source="component:portal"
        canManageArchitectureRelationships
        fetchRelations={async () => []}
        fetchArchitectureRelationships={async () => [manualRelationship]}
      /></MemoryRouter></ThemeProvider>,
    )

    await waitFor(() => expect(screen.getByRole('button', { name: 'Delete' })).toBeDefined())
    fireEvent.click(screen.getByRole('button', { name: 'Delete' }))

    await waitFor(() => expect(screen.getByText(/cannot be undone/i)).toBeDefined())
    fireEvent.click(screen.getByText('Cancel'))

    await waitFor(() => expect(screen.queryByText(/cannot be undone/i)).toBeNull())
    expect(architectureRelationshipsApi.remove).not.toHaveBeenCalled()
  })

  // The target lookup's combobox trigger renders its placeholder as plain content, not an
  // accessible name (role="combobox" doesn't take a name-from-content), so tests open it by
  // its visible placeholder text rather than by accessible role name.
  function openTargetLookup() {
    fireEvent.click(screen.getByText('Search Systems, Components, APIs, Resources, Users, Groups'))
  }

  it('filters the target lookup by search text across every supported kind', async () => {
    renderRelations(true)
    fireEvent.click(await screen.findByRole('button', { name: 'Add relationship' }))
    openTargetLookup()
    await waitFor(() => expect(screen.getByRole('option', { name: /Orders API/i })).toBeDefined())
    expect(screen.getByRole('option', { name: /Jane Doe/i })).toBeDefined()

    fireEvent.change(screen.getByPlaceholderText('Search by name...'), { target: { value: 'jane' } })
    await waitFor(() => expect(screen.queryByRole('option', { name: /Orders API/i })).toBeNull())
    expect(screen.getByRole('option', { name: /Jane Doe/i })).toBeDefined()
  })

  it('submits the canonical target ref for a selected catalog record', async () => {
    vi.mocked(architectureRelationshipsApi.create).mockResolvedValue(architectureRelationship)
    renderRelations(true)
    fireEvent.click(await screen.findByRole('button', { name: 'Add relationship' }))
    openTargetLookup()
    fireEvent.click(await screen.findByRole('option', { name: /Orders API/i }))
    fireEvent.change(screen.getByPlaceholderText('Makes API calls to'), { target: { value: 'Reads orders from' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create' }))
    await waitFor(() => expect(architectureRelationshipsApi.create).toHaveBeenCalledWith(
      expect.objectContaining({ target: 'api:orders-api', label: 'Reads orders from' }),
    ))
  })

  it('lets an editor select a User actor as the target', async () => {
    vi.mocked(architectureRelationshipsApi.create).mockResolvedValue(architectureRelationship)
    renderRelations(true)
    fireEvent.click(await screen.findByRole('button', { name: 'Add relationship' }))
    openTargetLookup()
    fireEvent.click(await screen.findByRole('option', { name: /Jane Doe/i }))
    await waitFor(() => expect(screen.getByText('User Jane Doe')).toBeDefined())
    fireEvent.change(screen.getByPlaceholderText('Makes API calls to'), { target: { value: 'Places an order' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create' }))
    await waitFor(() => expect(architectureRelationshipsApi.create).toHaveBeenCalledWith(
      expect.objectContaining({ target: 'user:jane-doe', label: 'Places an order' }),
    ))
  })

  it('hides manual relationship authoring controls for a read-only session even on a manageable entity (catalog-web-ui spec)', async () => {
    mockSession(true)
    const manualRelationship = { ...architectureRelationship, origin: 'manual' as const, source: 'component:portal' }
    render(
      <ThemeProvider theme="light"><MemoryRouter><RelationsTab
        source="component:portal"
        canManageArchitectureRelationships
        fetchRelations={async () => []}
        fetchArchitectureRelationships={async () => [manualRelationship]}
      /></MemoryRouter></ThemeProvider>,
    )

    await waitFor(() => expect(screen.getByText('Architecture Relationships')).toBeDefined())
    expect(screen.queryByRole('button', { name: 'Add relationship' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Edit' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Delete' })).toBeNull()
  })
})
