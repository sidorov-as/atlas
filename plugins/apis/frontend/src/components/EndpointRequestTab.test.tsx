// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import { ThemeProvider } from '@gravity-ui/uikit'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { EndpointRequestTab } from './EndpointRequestTab'
import { makeEndpoint } from '../testFixtures'

afterEach(() => cleanup())

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
vi.stubGlobal('ResizeObserver', ResizeObserverStub)

function renderTab(overrides: Parameters<typeof makeEndpoint>[0] = {}) {
  return render(
    <ThemeProvider theme="light">
      <EndpointRequestTab endpoint={makeEndpoint(overrides)} />
    </ThemeProvider>,
  )
}

describe('EndpointRequestTab', () => {
  it('shows no request-body section when the endpoint has no body', () => {
    renderTab({ request: { parameters: [], body: null } })
    expect(screen.queryByText(/Request body/)).toBeNull()
    expect(screen.getByText('No request parameters or body documented')).toBeDefined()
  })

  it('omits the fallback message once parameters exist, even with no body', () => {
    renderTab({
      request: {
        parameters: [{ name: 'id', location: 'path', required: true, description: '', schema: null }],
        body: null,
      },
    })
    expect(screen.getByText('Path parameters')).toBeDefined()
    expect(screen.queryByText('No request parameters or body documented')).toBeNull()
  })

  it('shows the request body schema and content type when a body is documented', () => {
    renderTab({
      request: {
        parameters: [],
        body: { contentType: 'application/json', schema: { type: 'string', '$ref': null, format: '', enum: null, nullable: false, description: '', properties: {}, required: [], items: null }, example: null },
      },
    })
    expect(screen.getByText('Request body (application/json)')).toBeDefined()
  })

  it('shows a copyable example when the body has one', () => {
    renderTab({
      request: {
        parameters: [],
        body: { contentType: 'application/json', schema: null, example: { id: '123' } },
      },
    })
    expect(screen.getByText('Example')).toBeDefined()
    expect(screen.getByText(/"id": "123"/)).toBeDefined()
  })

  it('omits parameter sections that have no parameters', () => {
    renderTab({
      request: {
        parameters: [{ name: 'id', location: 'path', required: true, description: '', schema: null }],
        body: null,
      },
    })
    expect(screen.queryByText('Query parameters')).toBeNull()
    expect(screen.queryByText('Header parameters')).toBeNull()
  })
})
