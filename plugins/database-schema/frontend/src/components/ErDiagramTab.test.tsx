// @vitest-environment jsdom
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { ThemeProvider } from '@gravity-ui/uikit'
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest'
import { ApiError } from 'frontend/lib/api'
import type { CatalogEntityUnion } from 'frontend/lib/types'
import { ErDiagramTab } from './ErDiagramTab'
import { databaseSchemaApi } from '../lib/databaseSchemaApi'

// `ErDiagramView`'s React Flow graph observes its container via
// `ResizeObserver`, which jsdom doesn't implement.
class ResizeObserverStub { observe() {} unobserve() {} disconnect() {} }
beforeAll(() => { globalThis.ResizeObserver = ResizeObserverStub as unknown as typeof ResizeObserver })

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

vi.mock('../lib/databaseSchemaApi', async () => {
  const actual = await vi.importActual<typeof import('../lib/databaseSchemaApi')>('../lib/databaseSchemaApi')
  return { ...actual, databaseSchemaApi: { get: vi.fn(), create: vi.fn(), update: vi.fn() } }
})

const entity = { id: 1, kind: 'Resource', capabilities: ['schema.host.v1'] } as unknown as CatalogEntityUnion

function renderTab() {
  return render(
    <ThemeProvider theme="light">
      <ErDiagramTab entity={entity} />
    </ThemeProvider>,
  )
}

describe('ErDiagramTab', () => {
  it('shows an empty state when no facet exists yet (entity-facets spec: "No ER Diagram tab without a facet")', async () => {
    vi.mocked(databaseSchemaApi.get).mockRejectedValue(new ApiError(404, null))
    renderTab()
    await waitFor(() => expect(screen.getByText(/No database schema is attached/)).toBeDefined())
  })

  it('shows a danger-themed error banner when the saved SQL failed to parse', async () => {
    vi.mocked(databaseSchemaApi.get).mockResolvedValue({
      entityId: '1', dialect: 'postgresql', sourceSql: 'garbage', parsedSchema: { tables: [] }, parseStatus: 'failed',
    })
    renderTab()
    await waitFor(() => expect(screen.getByText('The saved SQL failed to parse')).toBeDefined())
    expect(screen.getByText(/Fix the SQL on the Schema tab/)).toBeDefined()
  })

  it('renders the ER diagram for a successfully parsed schema', async () => {
    vi.mocked(databaseSchemaApi.get).mockResolvedValue({
      entityId: '1',
      dialect: 'postgresql',
      sourceSql: 'CREATE TABLE users (id uuid PRIMARY KEY);',
      parsedSchema: {
        tables: [{
          name: 'users', type: 'BASE TABLE',
          columns: [{ name: 'id', type: 'uuid', nullable: false, default: null }],
          indexes: [],
          constraints: [{ name: 'users_pkey', type: 'PRIMARY KEY', def: 'PRIMARY KEY (id)', table: 'users', columns: ['id'], referenced_table: null, referenced_columns: null }],
        }],
        relations: [],
        enums: [],
      },
      parseStatus: 'ok',
    })
    renderTab()
    await waitFor(() => expect(screen.getByText('users')).toBeDefined())
  })
})
