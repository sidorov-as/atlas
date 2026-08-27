// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import { ThemeProvider } from '@gravity-ui/uikit'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { EndpointParameterTable } from './EndpointParameterTable'
import type { EndpointParameter } from '../lib/types'

afterEach(() => cleanup())

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
vi.stubGlobal('ResizeObserver', ResizeObserverStub)

function makeParameter(overrides: Partial<EndpointParameter> = {}): EndpointParameter {
  return {
    name: 'id',
    location: 'path',
    required: true,
    description: '',
    schema: null,
    ...overrides,
  }
}

function renderTable(parameters: EndpointParameter[]) {
  return render(
    <ThemeProvider theme="light">
      <EndpointParameterTable title="Path parameters" parameters={parameters} />
    </ThemeProvider>,
  )
}

describe('EndpointParameterTable', () => {
  it('renders nothing when there are no parameters', () => {
    const { container } = renderTable([])
    expect(container.firstChild).toBeNull()
  })

  it('shows the bare type when no format is present', () => {
    renderTable([makeParameter({ schema: { type: 'string', '$ref': null, format: '', enum: null, nullable: false, description: '', properties: {}, required: [], items: null } })])
    expect(screen.getByText('string')).toBeDefined()
  })

  it('shows type and format together, e.g. "string (uuid)"', () => {
    renderTable([makeParameter({ schema: { type: 'string', '$ref': null, format: 'uuid', enum: null, nullable: false, description: '', properties: {}, required: [], items: null } })])
    expect(screen.getByText('string (uuid)')).toBeDefined()
  })

  it('shows the allowed enum values when present', () => {
    renderTable([makeParameter({
      name: 'status',
      location: 'query',
      schema: { type: 'string', '$ref': null, format: '', enum: ['active', 'removed'], nullable: false, description: '', properties: {}, required: [], items: null },
    })])
    expect(screen.getByText('Allowed: active, removed')).toBeDefined()
  })

  it('shows no allowed-values line when the schema has no enum', () => {
    renderTable([makeParameter({ schema: { type: 'string', '$ref': null, format: '', enum: null, nullable: false, description: '', properties: {}, required: [], items: null } })])
    expect(screen.queryByText(/Allowed:/)).toBeNull()
  })

  it('shows "—" for the type when the parameter has no schema', () => {
    renderTable([makeParameter({ schema: null })])
    // "—" also appears in the Description cell (empty description), so both cells fall back to it.
    expect(screen.getAllByText('—')).toHaveLength(2)
  })
})
