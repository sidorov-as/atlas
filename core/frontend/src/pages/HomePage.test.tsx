// @vitest-environment jsdom
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { ThemeProvider } from '@gravity-ui/uikit'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { atlasConfig } from '../atlas.config'
import { HomePage } from './HomePage'
import { apisApi, catalogHomeSettingsApi, componentsApi, groupsApi, resourcesApi, systemsApi } from '../lib/entities'

afterEach(() => cleanup())

function page(count: number) {
  return { count, numPages: 1, perPage: 1, page: { number: 1, objectList: [] } }
}

vi.mock('../lib/entities', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/entities')>()
  return {
    ...actual,
    systemsApi: { ...actual.systemsApi, list: vi.fn() },
    componentsApi: { ...actual.componentsApi, list: vi.fn() },
    apisApi: { ...actual.apisApi, list: vi.fn() },
    resourcesApi: { ...actual.resourcesApi, list: vi.fn() },
    groupsApi: { ...actual.groupsApi, list: vi.fn() },
    catalogHomeSettingsApi: { get: vi.fn() },
  }
})

function renderHomePage() {
  return render(
    <ThemeProvider theme="light">
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    </ThemeProvider>,
  )
}

describe('HomePage', () => {
  it('renders configured catalog identity above the divider and catalog cards', async () => {
    vi.mocked(systemsApi.list).mockResolvedValue(page(0))
    vi.mocked(componentsApi.list).mockResolvedValue(page(0))
    vi.mocked(apisApi.list).mockResolvedValue(page(0))
    vi.mocked(resourcesApi.list).mockResolvedValue(page(0))
    vi.mocked(groupsApi.list).mockResolvedValue(page(0))
    vi.mocked(catalogHomeSettingsApi.get).mockResolvedValue({ aboutMarkdown: '' })

    const { container } = renderHomePage()

    expect(screen.getByText(atlasConfig.title)).toBeDefined()
    expect(screen.getByText(atlasConfig.tagline)).toBeDefined()
    expect(container.querySelector('hr')).not.toBeNull()
    expect(screen.getByText('Systems')).toBeDefined()
    expect(screen.getByText('Teams')).toBeDefined()
    await waitFor(() => expect(screen.getByText('No description')).toBeDefined())
  })

  it('shows each entity kind\'s count from its own list endpoint', async () => {
    vi.mocked(systemsApi.list).mockResolvedValue(page(3))
    vi.mocked(componentsApi.list).mockResolvedValue(page(7))
    vi.mocked(apisApi.list).mockResolvedValue(page(0))
    vi.mocked(resourcesApi.list).mockResolvedValue(page(2))
    vi.mocked(groupsApi.list).mockResolvedValue(page(1))
    vi.mocked(catalogHomeSettingsApi.get).mockResolvedValue({ aboutMarkdown: '' })

    renderHomePage()

    await waitFor(() => expect(screen.getByText('3')).toBeDefined())
    expect(screen.getByText('7')).toBeDefined()
    expect(screen.getByText('2')).toBeDefined()
    expect(screen.getByText('1')).toBeDefined()
    // A kind with zero entities still shows its count rather than being omitted.
    expect(screen.getByText('0')).toBeDefined()
  })

  it('renders the admin-editable "About this catalog" content as Markdown', async () => {
    vi.mocked(systemsApi.list).mockResolvedValue(page(0))
    vi.mocked(componentsApi.list).mockResolvedValue(page(0))
    vi.mocked(apisApi.list).mockResolvedValue(page(0))
    vi.mocked(resourcesApi.list).mockResolvedValue(page(0))
    vi.mocked(groupsApi.list).mockResolvedValue(page(0))
    vi.mocked(catalogHomeSettingsApi.get).mockResolvedValue({ aboutMarkdown: '# Welcome to Atlas' })

    renderHomePage()

    await waitFor(() => expect(screen.getByText('About this catalog')).toBeDefined())
    expect(await screen.findByRole('heading', { name: 'Welcome to Atlas' })).toBeDefined()
  })

  // The System Landscape diagram moved off Home into `atlas.c4`'s own "System Map"
  // nav destination — its own coverage
  // now lives in `@atlas/plugin-c4`'s `SystemMapPage.test.tsx`. `composedContributions
  // .homeWidgets` stays wired into `HomePage.tsx` but is empty until a future
  // contribution populates it again.
})
