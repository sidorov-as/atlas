// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { ThemeProvider } from '@gravity-ui/uikit'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from 'frontend/lib/api'
import { useSession } from 'frontend/lib/SessionContext'
import type { CatalogEntityUnion } from 'frontend/lib/types'
import { SchemaEditorTab } from './SchemaEditorTab'
import { databaseSchemaApi } from '../lib/databaseSchemaApi'

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

vi.mock('../lib/databaseSchemaApi', async () => {
  const actual = await vi.importActual<typeof import('../lib/databaseSchemaApi')>('../lib/databaseSchemaApi')
  return { ...actual, databaseSchemaApi: { get: vi.fn(), create: vi.fn(), update: vi.fn() } }
})

vi.mock('frontend/lib/SessionContext', () => ({
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

// Same pattern as FlowFormPage.test.tsx: stub Monaco's `Editor` with a plain
// textarea so the SQL editor is exercisable via fireEvent without a real
// Monaco mount in jsdom.
vi.mock('@monaco-editor/react', () => ({
  Editor: ({ value, onChange }: { value: string, onChange: (value: string) => void }) => (
    <textarea aria-label="SQL" value={value} onChange={(event) => onChange(event.target.value)} />
  ),
}))

const entity = { id: 1, kind: 'Resource', capabilities: ['schema.host.v1'] } as unknown as CatalogEntityUnion

function renderTab() {
  return render(
    <ThemeProvider theme="light">
      <SchemaEditorTab entity={entity} />
    </ThemeProvider>,
  )
}

describe('SchemaEditorTab', () => {
  beforeEach(() => mockSession(false))

  it('starts with an empty editor and creates the facet with the default dialect on save when none exists yet', async () => {
    vi.mocked(databaseSchemaApi.get).mockRejectedValue(new ApiError(404, null))
    vi.mocked(databaseSchemaApi.create).mockResolvedValue({
      entityId: '1', dialect: 'postgresql', sourceSql: 'CREATE TABLE users (id uuid PRIMARY KEY);', parsedSchema: { tables: [] }, parseStatus: 'ok',
    })
    renderTab()

    const textarea = await screen.findByLabelText('SQL')
    expect((textarea as HTMLTextAreaElement).value).toBe('')
    expect(screen.getByText('PostgreSQL')).toBeDefined()

    fireEvent.change(textarea, { target: { value: 'CREATE TABLE users (id uuid PRIMARY KEY);' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save schema' }))

    await waitFor(() => expect(databaseSchemaApi.create).toHaveBeenCalledWith(1, 'CREATE TABLE users (id uuid PRIMARY KEY);', 'postgresql'))
    expect(databaseSchemaApi.update).not.toHaveBeenCalled()
  })

  it('updates the existing facet on save, and preserves a failed-parse edit with a visible indicator', async () => {
    vi.mocked(databaseSchemaApi.get).mockResolvedValue({
      entityId: '1', dialect: 'postgresql', sourceSql: 'CREATE TABLE users (id uuid PRIMARY KEY);', parsedSchema: { tables: [] }, parseStatus: 'ok',
    })
    vi.mocked(databaseSchemaApi.update).mockResolvedValue({
      entityId: '1', dialect: 'postgresql', sourceSql: 'garbage', parsedSchema: { tables: [] }, parseStatus: 'failed',
    })
    renderTab()

    const textarea = await screen.findByDisplayValue('CREATE TABLE users (id uuid PRIMARY KEY);')
    fireEvent.change(textarea, { target: { value: 'garbage' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save schema' }))

    await waitFor(() => expect(databaseSchemaApi.update).toHaveBeenCalledWith(1, 'garbage', 'postgresql'))
    expect(databaseSchemaApi.create).not.toHaveBeenCalled()
    await waitFor(() => expect(screen.getByText('Parse failed')).toBeDefined())
    expect((screen.getByDisplayValue('garbage') as HTMLTextAreaElement).value).toBe('garbage')
  })

  it('seeds the dialect select from the loaded facet and sends the chosen dialect on save', async () => {
    vi.mocked(databaseSchemaApi.get).mockResolvedValue({
      entityId: '1', dialect: 'mysql', sourceSql: 'CREATE TABLE users (id INT PRIMARY KEY);', parsedSchema: { tables: [] }, parseStatus: 'ok',
    })
    vi.mocked(databaseSchemaApi.update).mockResolvedValue({
      entityId: '1', dialect: 'mssql', sourceSql: 'CREATE TABLE users (id INT PRIMARY KEY);', parsedSchema: { tables: [] }, parseStatus: 'ok',
    })
    renderTab()

    await screen.findByDisplayValue('CREATE TABLE users (id INT PRIMARY KEY);')
    expect(screen.getByText('MySQL')).toBeDefined()

    fireEvent.click(screen.getByText('MySQL'))
    fireEvent.click(await screen.findByText('MS SQL'))
    fireEvent.click(screen.getByRole('button', { name: 'Save schema' }))

    await waitFor(() => expect(databaseSchemaApi.update).toHaveBeenCalledWith(
      1, 'CREATE TABLE users (id INT PRIMARY KEY);', 'mssql',
    ))
  })

  it('shows the saved SQL read-only, with no Save control, for a read-only session', async () => {
    mockSession(true)
    vi.mocked(databaseSchemaApi.get).mockResolvedValue({
      entityId: '1', dialect: 'postgresql', sourceSql: 'CREATE TABLE users (id uuid PRIMARY KEY);', parsedSchema: { tables: [] }, parseStatus: 'ok',
    })
    renderTab()

    await waitFor(() => expect(screen.getByText('CREATE TABLE users (id uuid PRIMARY KEY);')).toBeDefined())
    expect(screen.queryByLabelText('SQL')).toBeNull()
    expect(screen.queryByRole('button', { name: 'Save schema' })).toBeNull()
  })
})
