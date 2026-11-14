import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Alert, Breadcrumbs, Button, Loader, Text } from '@gravity-ui/uikit'
import { ConfirmDialog } from 'frontend/components/ConfirmDialog'
import { ApiError, errorMessage } from 'frontend/lib/api'
import { useSession } from 'frontend/lib/SessionContext'
import { useTheme } from 'frontend/lib/ThemeContext'
import { useAsync } from 'frontend/lib/useAsync'
import { useConfirm } from 'frontend/lib/useConfirm'
import { useFillViewportHeight } from 'frontend/lib/useFillViewportHeight'
import { DiagramViewer } from '../components/DiagramTab'
import { VIEWS_LIST_PATH, viewDiagramUrl, viewEditPath } from '../lib/customView'
import { viewsApi, type CustomViewFetchError } from '../lib/customViewApi'
import { failureMessage, isRenderFailure } from '../lib/customViewErrors'
import { useDiagramPreferences } from '../lib/diagramPreferences'

function ViewDiagram({ id, reloadToken, onError }: { id: string; reloadToken: number; onError: (error: CustomViewFetchError | null) => void }) {
  const [preferences, setPreferences] = useDiagramPreferences('custom')
  const { containerRef, height } = useFillViewportHeight()
  const { resolved: theme } = useTheme()
  return (
    <div ref={containerRef}>
      <DiagramViewer
        src={viewDiagramUrl(id, { rendering: preferences, theme })}
        alt="View diagram"
        fetchSource
        reloadToken={reloadToken}
        preferences={preferences}
        onPreferencesChange={setPreferences}
        downloadUrls={{
          svg: viewDiagramUrl(id, { download: true, rendering: preferences, theme }),
          png: viewDiagramUrl(id, { format: 'png', download: true, rendering: preferences, theme }),
        }}
        onFetchingChange={(fetching) => { if (fetching) onError(null) }}
        onFetchError={onError}
        height={height}
      />
    </div>
  )
}

/** A saved view: its diagram, with Edit and Delete for users who may write. */
export function ViewDetailPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const { session } = useSession()
  const isReadOnly = Boolean(session?.isReadOnly)
  const { data: view, error, isLoading } = useAsync(() => viewsApi.get(id), [id])
  const [diagramError, setDiagramError] = useState<CustomViewFetchError | null>(null)
  const [reloadToken, setReloadToken] = useState(0)
  const [actionError, setActionError] = useState<string | null>(null)
  const { confirm, dialogProps } = useConfirm()

  if (isLoading && !view) return <Loader size="m" />
  if (!view) {
    const notFound = error instanceof ApiError && error.status === 404
    return (
      <section>
        <Text as="h1" variant="header-1">{notFound ? 'View not found' : 'The view could not be loaded'}</Text>
        <p><Text color="secondary">{notFound ? 'It may have been deleted.' : errorMessage(error, 'Please try again later.')}</Text></p>
        <Button view="outlined" onClick={() => navigate(VIEWS_LIST_PATH)}>Back to views</Button>
      </section>
    )
  }

  async function handleDelete() {
    if (!view || !(await confirm({ title: 'Delete view', message: `Delete "${view.name}"? This cannot be undone.`, confirmText: 'Delete', preset: 'danger' }))) return
    try {
      await viewsApi.remove(view.id)
      navigate(VIEWS_LIST_PATH)
    } catch (err) {
      setActionError(errorMessage(err, 'The view could not be deleted'))
    }
  }

  const missing = view.missingEntities.length > 0

  return (
    <section aria-labelledby="view-heading" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <Breadcrumbs>
        <Breadcrumbs.Item
          href={VIEWS_LIST_PATH}
          onClick={(event) => {
            event.preventDefault()
            navigate(VIEWS_LIST_PATH)
          }}
        >
          Views
        </Breadcrumbs.Item>
        <Breadcrumbs.Item>{view.name}</Breadcrumbs.Item>
      </Breadcrumbs>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
        <div style={{ minWidth: 0 }}>
          <Text as="h1" id="view-heading" variant="header-1" style={{ margin: 0 }}>{view.name}</Text>
          {view.description && <p style={{ margin: '4px 0 0' }}><Text color="secondary">{view.description}</Text></p>}
        </div>
        {!isReadOnly && (
          <div style={{ display: 'flex', gap: 8 }}>
            <Button view="outlined" onClick={() => navigate(viewEditPath(view.id))}>Edit</Button>
            <Button view="outlined-danger" onClick={() => void handleDelete()}>Delete</Button>
          </div>
        )}
      </div>
      {actionError && <Alert theme="danger" message={actionError} />}
      {missing && (
        <Alert
          theme="warning"
          title="Some entities in this view no longer exist"
          message={`Missing: ${view.missingEntities.join(', ')}. ${isReadOnly ? '' : 'Edit the view to remove them.'}`}
        />
      )}
      {diagramError && !missing && (
        <Alert
          theme="danger"
          message={failureMessage(diagramError, false)}
          actions={isRenderFailure(diagramError) ? <Button view="outlined" onClick={() => setReloadToken((value) => value + 1)}>Retry</Button> : undefined}
        />
      )}
      {!missing && <ViewDiagram id={view.id} reloadToken={reloadToken} onError={setDiagramError} />}
      <ConfirmDialog {...dialogProps} />
    </section>
  )
}
