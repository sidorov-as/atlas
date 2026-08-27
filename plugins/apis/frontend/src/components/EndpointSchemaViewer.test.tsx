// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { ThemeProvider } from '@gravity-ui/uikit'
import { afterEach, describe, expect, it } from 'vitest'
import { EndpointSchemaViewer } from './EndpointSchemaViewer'
import type { EndpointSchema } from '../lib/types'

afterEach(() => cleanup())

/** Fills in every `EndpointSchema` field with a neutral default so each test
 * only spells out what it cares about — mirrors this plugin's resolved
 * (expanded) schema shape now that `$ref`s are resolved at sync time
 * not the old bare-`$ref` verbatim shape. */
function schema(overrides: Partial<EndpointSchema> = {}): EndpointSchema {
  return {
    type: null,
    '$ref': null,
    format: '',
    enum: null,
    nullable: false,
    description: '',
    properties: {},
    required: [],
    items: null,
    ...overrides,
  }
}

function renderSchema(value: EndpointSchema) {
  return render(
    <ThemeProvider theme="light">
      <EndpointSchemaViewer schema={value} />
    </ThemeProvider>,
  )
}

describe('EndpointSchemaViewer', () => {
  it('renders a resolved schema tree with nested properties expanded', () => {
    renderSchema(
      schema({
        type: 'object',
        properties: {
          id: schema({ type: 'string' }),
          total: schema({
            type: 'object',
            properties: { amount: schema({ type: 'number' }), currency: schema({ type: 'string' }) },
          }),
        },
        required: ['id'],
      }),
    )

    expect(screen.getByText('id')).toBeDefined()
    expect(screen.getByText('total')).toBeDefined()

    fireEvent.click(screen.getByLabelText('Expand'))

    expect(screen.getByText('amount')).toBeDefined()
    expect(screen.getByText('currency')).toBeDefined()
  })

  it('still renders an unresolved $ref as a labeled leaf at a cycle point', () => {
    renderSchema(
      schema({
        type: 'object',
        properties: {
          children: schema({ '$ref': '#/components/schemas/Category' }),
        },
      }),
    )

    expect(screen.getByText('children')).toBeDefined()
    expect(screen.getByText('Category')).toBeDefined()
  })

  it('renders a description merged onto a resolved schema node (merge_siblings=True)', () => {
    renderSchema(
      schema({
        type: 'object',
        description: 'override',
        properties: { id: schema({ type: 'string' }) },
      }),
    )

    expect(screen.getByText('override')).toBeDefined()
  })
})
