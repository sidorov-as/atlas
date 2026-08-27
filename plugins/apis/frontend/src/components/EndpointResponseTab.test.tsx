// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import { ThemeProvider } from '@gravity-ui/uikit'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { EndpointResponseTab } from './EndpointResponseTab'
import { makeEndpoint } from '../testFixtures'
import type { EndpointResponse } from '../lib/types'

afterEach(() => cleanup())

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

function response(statusCode: string, overrides: Partial<EndpointResponse> = {}): EndpointResponse {
  return { statusCode, description: '', contentType: '', schema: null, example: null, headers: {}, ...overrides }
}

function renderTab(responses: EndpointResponse[]) {
  return render(
    <ThemeProvider theme="light">
      <EndpointResponseTab endpoint={makeEndpoint({ responses })} />
    </ThemeProvider>,
  )
}

describe('EndpointResponseTab', () => {
  it('shows "No responses documented" when there are none', () => {
    renderTab([])
    expect(screen.getByText('No responses documented')).toBeDefined()
  })

  it('defaults to the first 2xx response, per spec\'s 401/200/404 scenario', () => {
    renderTab([response('401'), response('200'), response('404')])
    expect(screen.getByText('200', { selector: '.g-label__content' })).toBeDefined()
  })

  it('falls back to the first response when none is 2xx, per spec\'s 400/404 scenario', () => {
    renderTab([response('400'), response('404')])
    expect(screen.getByText('400', { selector: '.g-label__content' })).toBeDefined()
  })

  it('shows the selected response\'s content type', () => {
    renderTab([response('200', { contentType: 'application/json' })])
    expect(screen.getByText('application/json')).toBeDefined()
  })

  it('shows a copyable example when the response has one', () => {
    renderTab([response('200', { example: { ok: true } })])
    expect(screen.getByText('Example')).toBeDefined()
    expect(screen.getByText(/"ok": true/)).toBeDefined()
  })

  it('shows no example section when the response has none', () => {
    renderTab([response('200', { example: null })])
    expect(screen.queryByText('Example')).toBeNull()
  })

  it('shows no Headers section when the response has none', () => {
    renderTab([response('200')])
    expect(screen.queryByText('Headers')).toBeNull()
  })

  it('shows the response headers when present', () => {
    renderTab([response('200', {
      headers: { 'X-Rate-Limit': { description: 'Requests remaining', schema: { type: 'integer', '$ref': null, format: '', enum: null, nullable: false, description: '', properties: {}, required: [], items: null } } },
    })])
    expect(screen.getByText('Headers')).toBeDefined()
    expect(screen.getByText('X-Rate-Limit')).toBeDefined()
    expect(screen.getByText('integer')).toBeDefined()
    expect(screen.getByText('Requests remaining')).toBeDefined()
  })
})
