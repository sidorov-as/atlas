// @vitest-environment jsdom
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { ThemeProvider } from '@gravity-ui/uikit'
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest'
import { ErDiagramView, inlineEdgeStrokeStyles } from './ErDiagramView'
import type { ParsedSchema } from '../lib/databaseSchemaApi'

// React Flow observes its container's size via `ResizeObserver`, which
// jsdom doesn't implement (same stub pattern as RelationsTab.test.tsx /
// EntityListPage.test.tsx).
class ResizeObserverStub { observe() {} unobserve() {} disconnect() {} }
beforeAll(() => { globalThis.ResizeObserver = ResizeObserverStub as unknown as typeof ResizeObserver })

afterEach(() => cleanup())

function renderView(schema: ParsedSchema) {
  return render(
    <ThemeProvider theme="light">
      <ErDiagramView schema={schema} />
    </ThemeProvider>,
  )
}

const USERS_ORDERS_SCHEMA: ParsedSchema = {
  tables: [
    {
      name: 'users',
      type: 'BASE TABLE',
      columns: [
        { name: 'id', type: 'uuid', nullable: false, default: null },
        { name: 'email', type: 'varchar(255)', nullable: false, default: null },
      ],
      indexes: [],
      constraints: [
        { name: 'users_pkey', type: 'PRIMARY KEY', def: 'PRIMARY KEY (id)', table: 'users', columns: ['id'], referenced_table: null, referenced_columns: null },
      ],
    },
    {
      name: 'orders',
      type: 'BASE TABLE',
      columns: [
        { name: 'id', type: 'uuid', nullable: false, default: null },
        { name: 'user_id', type: 'uuid', nullable: true, default: null },
      ],
      indexes: [],
      constraints: [
        { name: 'orders_pkey', type: 'PRIMARY KEY', def: 'PRIMARY KEY (id)', table: 'orders', columns: ['id'], referenced_table: null, referenced_columns: null },
        { name: 'orders_user_id_fkey', type: 'FOREIGN KEY', def: 'FOREIGN KEY (user_id) REFERENCES users(id)', table: 'orders', columns: ['user_id'], referenced_table: 'users', referenced_columns: ['id'] },
      ],
    },
  ],
  relations: [
    { table: 'orders', columns: ['user_id'], parent_table: 'users', parent_columns: ['id'], cardinality: 'many_to_one' },
  ],
  enums: [],
}

describe('ErDiagramView', () => {
  it('renders every table and column as a graph node', async () => {
    renderView(USERS_ORDERS_SCHEMA)

    await waitFor(() => expect(screen.getByText('users')).toBeDefined())
    expect(screen.getByText('orders')).toBeDefined()
    expect(screen.getByText('email')).toBeDefined()
    expect(screen.getByText('user_id')).toBeDefined()
  })

  it('shows an empty state when there are no tables', () => {
    renderView({ tables: [], relations: [], enums: [] })
    expect(screen.getByText('This schema has no tables.')).toBeDefined()
  })

  it('shows a re-save prompt for an old-shape parsed_schema without a top-level relations array', () => {
    renderView({ tables: [{ name: 'users', columns: [] }] } as unknown as ParsedSchema)
    expect(screen.getByText(/saved before the ER Diagram upgrade/)).toBeDefined()
  })

  // Regression test for `inlineEdgeStrokeStyles`: `html-to-image` never
  // inlines computed style onto anything nested inside an `<svg>` (it
  // deep-clones the `<svg>` natively instead of walking its children), and
  // React Flow's edge paths get their stroke only from an external CSS
  // class — so an export silently dropped every relation line. Exercised
  // directly against a hand-built DOM fragment (rather than through
  // `ErDiagramView`'s own rendered edges) because React Flow doesn't render
  // `<path>` edges under jsdom, which has no real layout engine to measure
  // node/handle positions from.
  describe('inlineEdgeStrokeStyles', () => {
    function buildEdgeFragment(): { root: HTMLElement, path: SVGPathElement } {
      const root = document.createElement('div')
      root.innerHTML = '<div class="react-flow__edges"><svg><path class="react-flow__edge-path" d="M0,0 L1,1"></path></svg></div>'
      const path = root.querySelector('.react-flow__edge-path') as unknown as SVGPathElement
      return { root, path }
    }

    it('resolves each edge path\'s computed stroke onto its own inline style', () => {
      const { root, path } = buildEdgeFragment()
      const originalGetComputedStyle = window.getComputedStyle
      const getComputedStyleSpy = vi.spyOn(window, 'getComputedStyle').mockImplementation((element, pseudo) => {
        const real = originalGetComputedStyle(element, pseudo ?? undefined)
        if ((element as Element) === (path as unknown as Element)) {
          return { ...real, stroke: 'rgb(1, 2, 3)', strokeWidth: '2px', fill: 'none' } as CSSStyleDeclaration
        }
        return real
      })

      expect(path.getAttribute('style')).toBeNull()
      inlineEdgeStrokeStyles(root)

      expect(path.getAttribute('style')).toContain('stroke: rgb(1, 2, 3)')
      expect(path.getAttribute('style')).toContain('stroke-width: 2px')

      getComputedStyleSpy.mockRestore()
    })

    it('reverts the inlined style when the returned cleanup function runs', () => {
      const { root, path } = buildEdgeFragment()

      const restore = inlineEdgeStrokeStyles(root)
      expect(path.hasAttribute('style')).toBe(true)

      restore()
      expect(path.getAttribute('style')).toBeNull()
    })

    it('restores a pre-existing inline style rather than clearing it', () => {
      const { root, path } = buildEdgeFragment()
      path.setAttribute('style', 'stroke: red;')

      const restore = inlineEdgeStrokeStyles(root)
      restore()

      expect(path.getAttribute('style')).toBe('stroke: red;')
    })
  })
})
