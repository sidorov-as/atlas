import { Alert, Card, Loader, Text } from '@gravity-ui/uikit'
import { Link } from 'react-router-dom'
import { ErrorBoundary } from 'react-error-boundary'
import { MarkdownDescription } from '../components/MarkdownDescription'
import { atlasConfig } from '../atlas.config'
import { apisApi, catalogHomeSettingsApi, componentsApi, groupsApi, resourcesApi, systemsApi } from '../lib/entities'
import { useAsync } from '../lib/useAsync'
import { composedContributions } from '../plugins/composition'

/**
 * Entity-kind counts row — one list-endpoint call per kind,
 * reading its pagination total. `api` is stored rather than `api.list` directly so this
 * array can live at module scope without eagerly dereferencing a method off it.
 */
const COUNT_SECTIONS = [
  { to: '/systems', label: 'Systems', api: systemsApi },
  { to: '/components', label: 'Components', api: componentsApi },
  { to: '/apis', label: 'APIs', api: apisApi },
  { to: '/resources', label: 'Resources', api: resourcesApi },
  { to: '/teams', label: 'Teams', api: groupsApi },
]

export function HomePage() {
  const { data: counts } = useAsync(
    () => Promise.all(COUNT_SECTIONS.map((section) => section.api.list({ pageSize: 1 }))),
    [],
  )
  const { data: homeSettings, isLoading: isHomeSettingsLoading } = useAsync(
    () => catalogHomeSettingsApi.get(),
    [],
  )

  return (
    <div>
      <Text variant="header-1">{atlasConfig.title}</Text>
      <p>
        <Text color="secondary">{atlasConfig.tagline}</Text>
      </p>
      <hr style={{ margin: '24px 0' }} />

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 16 }}>
        {COUNT_SECTIONS.map((section, index) => (
          <Link key={section.to} to={section.to} style={{ textDecoration: 'none' }}>
            <Card view="outlined" style={{ padding: 16, textAlign: 'center' }}>
              <Text variant="display-1">{counts ? counts[index].count : '—'}</Text>
              <p>
                <Text color="secondary">{section.label}</Text>
              </p>
            </Card>
          </Link>
        ))}
      </div>

      <div style={{ marginTop: 40 }}>
        <Text variant="header-2">About this catalog</Text>
        <div style={{ marginTop: 12 }}>
          {isHomeSettingsLoading ? (
            <Loader size="s" />
          ) : (
            <MarkdownDescription text={homeSettings?.aboutMarkdown ?? ''} />
          )}
        </div>
      </div>

      {/* `homeWidgets` has no contributor since the System Landscape widget moved to `atlas.c4`'s own "System Map" nav destination — kept wired for a future contribution. */}
      {composedContributions.homeWidgets.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24, marginTop: 40 }}>
          {composedContributions.homeWidgets.map((widget) => (
            <ErrorBoundary key={widget.id} fallback={<Alert theme="danger" message="This widget failed to load." />}>
              <widget.component />
            </ErrorBoundary>
          ))}
        </div>
      )}
    </div>
  )
}
