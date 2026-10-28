import { Loader, Tab, TabList, TabPanel, TabProvider, Text } from '@gravity-ui/uikit'
import { useSearchParams } from 'react-router-dom'
import { systemsApi } from 'frontend/lib/entities'
import { useAsync } from 'frontend/lib/useAsync'
import { useFillViewportHeight } from 'frontend/lib/useFillViewportHeight'
import { DiagramViewer } from '../components/DiagramTab'
import { ViewsList } from '../components/ViewsList'
import { VIEWS_TAB } from '../lib/customView'
import { useDiagramPreferences, type DiagramRenderingPreferences } from '../lib/diagramPreferences'
import { systemLandscapeUrl } from '../lib/diagramUrls'

/** Mounted only once loading has finished and there's a diagram to show, so `useFillViewportHeight`'s
 * container ref exists from this component's very first render — calling that hook from `SystemMapPage`
 * itself would measure while this div doesn't exist yet (the hook's own documented anti-pattern), the
 * same reason `FlowDetailPage`'s `FlowCanvasPanel` is split out from its page component. */
function SystemMapDiagram({ preferences, onPreferencesChange }: {
  preferences: DiagramRenderingPreferences
  onPreferencesChange: (preferences: DiagramRenderingPreferences) => void
}) {
  const { containerRef, height } = useFillViewportHeight()
  return (
    <div ref={containerRef}>
      <DiagramViewer
        src={systemLandscapeUrl({ rendering: preferences })}
        alt="System Landscape diagram"
        preferences={preferences}
        onPreferencesChange={onPreferencesChange}
        downloadUrls={{
          svg: systemLandscapeUrl({ download: true, rendering: preferences }),
          png: systemLandscapeUrl({ format: 'png', download: true, rendering: preferences }),
        }}
        height={height}
      />
    </div>
  )
}

/**
 * `atlas.c4`'s own nav destination for the catalog-wide System Landscape
 * diagram, replacing the former Home
 * widget — `DiagramViewer`/`systemLandscapeUrl` reused unchanged.
 *
 * Systems are always rendered as nodes even without relationships, so the
 * real empty condition is zero Systems in the catalog, not zero
 * relationships — checked via the existing `systemsApi.list()` pagination
 * count rather than a new backend endpoint.
 */
function LandscapeTab() {
  const [diagramPreferences, setDiagramPreferences] = useDiagramPreferences('landscape')
  const { data: systems, isLoading } = useAsync(() => systemsApi.list({ pageSize: 1 }), [])

  return isLoading ? (
    <Loader size="m" />
  ) : systems?.count === 0 ? (
    <Text color="secondary">System Map appears once your catalog has systems.</Text>
  ) : (
    <SystemMapDiagram preferences={diagramPreferences} onPreferencesChange={setDiagramPreferences} />
  )
}

const LANDSCAPE_TAB = 'landscape'

/** System Map: the catalog-wide Landscape and the saved Views list, selected by the `tab` URL parameter. */
export function SystemMapPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const activeTab = searchParams.get('tab') === VIEWS_TAB ? VIEWS_TAB : LANDSCAPE_TAB

  return (
    <section aria-labelledby="system-map-heading">
      <Text id="system-map-heading" variant="header-1">System Map</Text>
      <p>
        <Text color="secondary">Relationships among catalog systems and explicitly interacting people.</Text>
      </p>
      <TabProvider
        value={activeTab}
        onUpdate={(tab) => setSearchParams(tab === VIEWS_TAB ? { tab } : {})}
      >
        <TabList>
          <Tab value={LANDSCAPE_TAB}>Landscape</Tab>
          <Tab value={VIEWS_TAB}>Views</Tab>
        </TabList>
        <TabPanel value={LANDSCAPE_TAB}>
          {activeTab === LANDSCAPE_TAB && <div style={{ paddingTop: 16 }}><LandscapeTab /></div>}
        </TabPanel>
        <TabPanel value={VIEWS_TAB}>
          {activeTab === VIEWS_TAB && <ViewsList />}
        </TabPanel>
      </TabProvider>
    </section>
  )
}
