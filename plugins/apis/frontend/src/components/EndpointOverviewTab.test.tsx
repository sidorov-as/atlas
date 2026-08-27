// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ThemeProvider } from '@gravity-ui/uikit'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { EndpointOverviewTab } from './EndpointOverviewTab'
import { makeApi, makeConsumers, makeEndpoint, makeServiceSummary } from '../testFixtures'

afterEach(() => cleanup())

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
vi.stubGlobal('ResizeObserver', ResizeObserverStub)

vi.mock('frontend/lib/entities', () => ({
  kindToPath: { system: '/systems', component: '/components', group: '/teams', api: '/apis' },
}))

vi.mock('frontend/lib/SessionContext', () => ({
  useSession: () => ({ session: { isAuthenticated: true, user: null }, isLoading: false, login: vi.fn(), logout: vi.fn() }),
}))

vi.mock('./EndpointConsumersGraph', () => ({
  EndpointConsumersGraph: () => <div>consumers graph</div>,
}))

function renderTab(overrides: Parameters<typeof makeEndpoint>[0] = {}, apiOverrides: Parameters<typeof makeApi>[0] = {}) {
  return render(
    <ThemeProvider theme="light">
      <MemoryRouter>
        <EndpointOverviewTab
          endpoint={makeEndpoint(overrides)}
          api={makeApi(apiOverrides)}
          consumers={makeConsumers()}
          consumersLoading={false}
          consumersError={null}
          onRetryConsumers={vi.fn()}
          onViewLinkedServices={vi.fn()}
          providerRelation={null}
        />
      </MemoryRouter>
    </ThemeProvider>,
  )
}

describe('EndpointOverviewTab', () => {
  it('shows the documentation card, even with no description', () => {
    renderTab({ description: '' })
    expect(screen.getByText('Documentation')).toBeDefined()
    expect(screen.getByText('No documentation')).toBeDefined()
  })

  it('omits path/query/header parameter sections when there are none', () => {
    renderTab({ request: { parameters: [], body: null } })
    expect(screen.queryByText('Path parameters')).toBeNull()
    expect(screen.queryByText('Query parameters')).toBeNull()
    expect(screen.queryByText('Header parameters')).toBeNull()
  })

  it('shows only the parameter sections that have parameters', () => {
    renderTab({
      request: {
        parameters: [
          { name: 'id', location: 'path', required: true, description: '', schema: null },
        ],
        body: null,
      },
    })
    expect(screen.getByText('Path parameters')).toBeDefined()
    expect(screen.queryByText('Query parameters')).toBeNull()
    expect(screen.queryByText('Header parameters')).toBeNull()
  })

  it('omits the responses table when there are no responses', () => {
    renderTab({ responses: [] })
    expect(screen.queryByText('Responses')).toBeNull()
  })

  it('shows a compact responses table when responses exist', () => {
    renderTab({
      responses: [{ statusCode: '200', description: 'OK', contentType: 'application/json', schema: null, example: null, headers: {} }],
    })
    expect(screen.getByText('Responses')).toBeDefined()
    expect(screen.getByText('200')).toBeDefined()
  })

  it('omits the Consumes/Produces row when no content types are present', () => {
    renderTab({ request: { parameters: [], body: null }, responses: [] })
    expect(screen.queryByText('Consumes/Produces')).toBeNull()
  })

  it('shows a deduplicated Consumes/Produces row from the request body and response content types', () => {
    renderTab({
      request: { parameters: [], body: { contentType: 'application/json', schema: null, example: null } },
      responses: [
        { statusCode: '200', description: 'OK', contentType: 'application/json', schema: null, example: null, headers: {} },
        { statusCode: '404', description: 'Not found', contentType: 'application/problem+json', schema: null, example: null, headers: {} },
      ],
    })
    expect(screen.getByText('Consumes/Produces')).toBeDefined()
    // Each content type also appears once in the responses table below, so the deduplicated
    // Consumes/Produces label accounts for exactly one of the two occurrences of each.
    expect(screen.getAllByText('application/json')).toHaveLength(2)
    expect(screen.getAllByText('application/problem+json')).toHaveLength(2)
  })

  it('omits Protocol/Base URL rows when the API has no resolved base URL/protocol', () => {
    renderTab({}, { resolvedBaseUrl: '', resolvedProtocol: '' })
    expect(screen.queryByText('Protocol')).toBeNull()
    expect(screen.queryByText('Base URL')).toBeNull()
  })

  it('shows Protocol and Base URL when resolved on the API', () => {
    renderTab({}, { resolvedBaseUrl: 'api.example.com/v1', resolvedProtocol: 'https' })
    expect(screen.getByText('Protocol')).toBeDefined()
    expect(screen.getByText('https')).toBeDefined()
    expect(screen.getByText('Base URL')).toBeDefined()
    expect(screen.getByText('api.example.com/v1')).toBeDefined()
  })

  it('shows Base URL without Protocol when only the base URL resolved (2.0 multiple schemes)', () => {
    renderTab({}, { resolvedBaseUrl: 'api.example.com/v1', resolvedProtocol: '' })
    expect(screen.queryByText('Protocol')).toBeNull()
    expect(screen.getByText('Base URL')).toBeDefined()
  })

  it('omits Security and External docs rows when the endpoint has neither', () => {
    renderTab({ security: [], externalDocs: null })
    expect(screen.queryByText('Security')).toBeNull()
    expect(screen.queryByText('External docs')).toBeNull()
  })

  it('shows a resolved Security label', () => {
    renderTab({ security: [{ type: 'http', scheme: 'bearer' }] })
    expect(screen.getByText('Security')).toBeDefined()
    expect(screen.getByText('http (bearer)')).toBeDefined()
  })

  it('shows the externalDocs link using its description, falling back to the URL', () => {
    renderTab({ externalDocs: { description: 'More info', url: 'https://example.com/docs' } })
    expect(screen.getByText('External docs')).toBeDefined()
    const link = screen.getByText('More info')
    expect(link.closest('a')).toHaveProperty('href', 'https://example.com/docs')
  })

  it("shows the parent API's owner and system in the Details card, not the endpoint's own", () => {
    renderTab()
    expect(screen.getByText('Owner')).toBeDefined()
    expect(screen.getByText('System')).toBeDefined()
    expect(screen.getByText('platform')).toBeDefined()
    expect(screen.getByText('core')).toBeDefined()
  })

  it('shows "Imported from spec" as the Source for a synced openapi API', () => {
    renderTab({}, { type: 'openapi', specContent: 'openapi: 3.0.0' })
    expect(screen.getByText('Source')).toBeDefined()
    expect(screen.getByText('Imported from spec')).toBeDefined()
  })

  it('shows "Manually authored" as the Source when the API has no resolved spec content', () => {
    renderTab({}, { type: 'openapi', specContent: '' })
    expect(screen.getByText('Manually authored')).toBeDefined()
  })

  it('links to the Linked Services tab from the "View all" link when there are linked services', () => {
    render(
      <ThemeProvider theme="light">
        <MemoryRouter>
          <EndpointOverviewTab
            endpoint={makeEndpoint()}
            api={makeApi()}
            consumers={makeConsumers([makeServiceSummary(), makeServiceSummary({ id: 'service-2', name: 'other' })])}
            consumersLoading={false}
            consumersError={null}
            onRetryConsumers={vi.fn()}
            onViewLinkedServices={vi.fn()}
            providerRelation={null}
          />
        </MemoryRouter>
      </ThemeProvider>,
    )
    expect(screen.getByText('View all 2 services')).toBeDefined()
  })

  it('shows no "View all" link when no services are linked', () => {
    renderTab()
    expect(screen.queryByText(/View all/)).toBeNull()
  })

  it('groups Details with the graph in the two-column grid, keeping parameters/responses outside it', () => {
    const { container } = renderTab({
      request: { parameters: [{ name: 'id', location: 'path', required: true, description: '', schema: null }], body: null },
      responses: [{ statusCode: '200', description: 'OK', contentType: 'application/json', schema: null, example: null, headers: {} }],
    })

    const grid = container.querySelector('.endpoint-overview-grid')
    expect(grid).not.toBeNull()
    // Left column: Documentation + Details. Right column: the graph.
    expect(grid!.contains(screen.getByText('Documentation'))).toBe(true)
    expect(grid!.contains(screen.getByText('Details'))).toBe(true)
    expect(grid!.contains(screen.getByText('consumers graph'))).toBe(true)
    // Parameters/responses moved to a full-width section below the grid.
    expect(grid!.contains(screen.getByText('Path parameters'))).toBe(false)
    expect(grid!.contains(screen.getByText('Responses'))).toBe(false)
  })
})
