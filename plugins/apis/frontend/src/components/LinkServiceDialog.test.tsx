// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { ThemeProvider } from '@gravity-ui/uikit'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { LinkServiceDialog } from './LinkServiceDialog'
import { componentsApi } from 'frontend/lib/entities'
import { endpointServicesApi } from '../lib/entities'
import { makeApi, makeEndpoint } from '../testFixtures'
import type { ComponentEntity } from 'frontend/lib/types'

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
vi.stubGlobal('ResizeObserver', ResizeObserverStub)
vi.stubGlobal('matchMedia', (query: string) => ({
  matches: false, media: query, onchange: null,
  addListener: () => {}, removeListener: () => {},
  addEventListener: () => {}, removeEventListener: () => {}, dispatchEvent: () => false,
}))

vi.mock('frontend/lib/entities', () => ({
  componentsApi: { list: vi.fn() },
}))

vi.mock('../lib/entities', () => ({
  endpointServicesApi: { link: vi.fn() },
}))

function makeComponent(overrides: Partial<ComponentEntity> = {}): ComponentEntity {
  return {
    id: 'service-1',
    apiVersion: 'atlas/v1alpha1',
    kind: 'Component',
    metadata: { name: 'billing-service', title: '', description: '', documentation: '', labels: {}, tags: [], tagColors: {}, links: [] },
    spec: {
      type: 'service', lifecycle: 'production', owner: 'group:platform', ownerId: 'group-1',
      system: 'system:core', systemId: 'system-1', providesApis: [], consumesApis: [], dependsOn: [],
    },
    status: 'active',
    ingestedFrom: null,
    blockedBy: null,
    blockedByReason: null,
    capabilities: [],
    ...overrides,
  }
}

function renderDialog(props: Partial<Parameters<typeof LinkServiceDialog>[0]> = {}) {
  const onClose = vi.fn()
  const onLinked = vi.fn()
  render(
    <ThemeProvider theme="light">
      <LinkServiceDialog
        open
        onClose={onClose}
        endpoint={makeEndpoint()}
        api={makeApi()}
        linkedServiceIds={new Set()}
        onLinked={onLinked}
        {...props}
      />
    </ThemeProvider>,
  )
  return { onClose, onLinked }
}

describe('LinkServiceDialog', () => {
  it('shows an "Already linked" marker for a service already linked to this endpoint', async () => {
    vi.mocked(componentsApi.list).mockResolvedValue({
      count: 1, numPages: 1, perPage: 100, page: { number: 1, objectList: [makeComponent()] },
    })
    renderDialog({ linkedServiceIds: new Set(['service-1']) })

    fireEvent.click(await screen.findByText('Select a service…'))
    await waitFor(() => expect(screen.getByText('Already linked')).toBeDefined())
  })

  it('shows an informational note that linking will also create consumesAPI when it will', async () => {
    vi.mocked(componentsApi.list).mockResolvedValue({
      count: 1, numPages: 1, perPage: 100, page: { number: 1, objectList: [makeComponent()] },
    })
    renderDialog()

    fireEvent.click(await screen.findByText('Select a service…'))
    fireEvent.click(await screen.findByText('billing-service'))

    await waitFor(() => expect(screen.getByText(/Linking will also mark billing-service as consuming billing-api/)).toBeDefined())
  })

  it('shows no consumesAPI note when the service already consumes the API', async () => {
    vi.mocked(componentsApi.list).mockResolvedValue({
      count: 1, numPages: 1, perPage: 100,
      page: { number: 1, objectList: [makeComponent({ spec: { ...makeComponent().spec, consumesApis: ['api:billing-api'] } })] },
    })
    renderDialog()

    fireEvent.click(await screen.findByText('Select a service…'))
    fireEvent.click(await screen.findByText('billing-service'))

    expect(screen.queryByText(/Linking will also mark/)).toBeNull()
  })

  it('submits the link and calls onLinked/onClose on success', async () => {
    vi.mocked(componentsApi.list).mockResolvedValue({
      count: 1, numPages: 1, perPage: 100, page: { number: 1, objectList: [makeComponent()] },
    })
    vi.mocked(endpointServicesApi.link).mockResolvedValue({
      id: 'usage-1',
      service: { id: 'service-1', ref: 'component:billing-service', name: 'billing-service', title: '', team: 'group:platform', teamId: 'group-1', teamName: 'platform' },
      linkedAt: '2026-01-01T00:00:00Z',
      apiRelationCreated: true,
    })
    const { onClose, onLinked } = renderDialog()

    fireEvent.click(await screen.findByText('Select a service…'))
    fireEvent.click(await screen.findByText('billing-service'))
    fireEvent.click(screen.getByText('Link'))

    await waitFor(() => expect(endpointServicesApi.link).toHaveBeenCalledWith('endpoint-1', 'service-1'))
    await waitFor(() => expect(onLinked).toHaveBeenCalled())
    expect(onClose).toHaveBeenCalled()
  })

  it('disables the Link button until a service is selected', async () => {
    vi.mocked(componentsApi.list).mockResolvedValue({
      count: 1, numPages: 1, perPage: 100, page: { number: 1, objectList: [makeComponent()] },
    })
    renderDialog()

    const button = screen.getByText('Link').closest('button')
    expect(button?.hasAttribute('disabled')).toBe(true)
  })
})
