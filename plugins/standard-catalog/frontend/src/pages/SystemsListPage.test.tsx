// @vitest-environment jsdom
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ThemeProvider } from '@gravity-ui/uikit'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { SystemDocumentationPreview } from './SystemsListPage'
import { systemsApi } from 'frontend/lib/entities'
import type { SystemEntity } from 'frontend/lib/types'

afterEach(() => cleanup())

vi.mock('frontend/lib/entities', async (importOriginal) => {
  const actual = await importOriginal<typeof import('frontend/lib/entities')>()
  return { ...actual, systemsApi: { ...actual.systemsApi, docs: vi.fn() } }
})

const system: SystemEntity = {
  id: 'system-1',
  apiVersion: 'atlas/v1alpha1',
  kind: 'System',
  metadata: { name: 'test', title: 'Test', description: '', documentation: '', labels: {}, tags: [], tagColors: {}, links: [] },
  spec: { owner: 'group:platform', ownerId: 'group-1' },
  status: 'active',
  ingestedFrom: null,
  blockedBy: null,
  blockedByReason: null,
  capabilities: [],
}

describe('SystemDocumentationPreview', () => {
  it('shows each documentation type as a label beside its link', async () => {
    vi.mocked(systemsApi.docs).mockResolvedValue({
      count: 2,
      numPages: 1,
      perPage: 5,
      page: {
        number: 1,
        objectList: [
          { title: 'Runbook', description: '', url: 'https://example.test/runbook', type: 'runbook' },
          { title: 'Metrics', description: '', url: 'https://example.test/metrics', type: 'dashboard' },
        ],
      },
    })

    render(
      <ThemeProvider theme="light">
        <MemoryRouter>
          <SystemDocumentationPreview system={system} />
        </MemoryRouter>
      </ThemeProvider>,
    )

    await waitFor(() => expect(screen.getByRole('link', { name: 'Runbook' })).toBeDefined())
    expect(screen.getByText('runbook')).toBeDefined()
    expect(screen.getByText('dashboard')).toBeDefined()
  })
})
