import { useEffect, useMemo, useRef, useState } from 'react'
import { LayoutColumns, LayoutSideContentRight } from '@gravity-ui/icons'
import { Alert, Breadcrumbs, Button, Icon, Loader, Text, TextArea, TextInput, Tooltip } from '@gravity-ui/uikit'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { ConfirmDialog } from 'frontend/components/ConfirmDialog'
import { HeaderActionRow } from 'frontend/components/HeaderActionRow'
import { ApiError, errorMessage } from 'frontend/lib/api'
import { useAsync } from 'frontend/lib/useAsync'
import { useFillViewportHeight } from 'frontend/lib/useFillViewportHeight'
import { DiagramViewer } from '../components/DiagramTab'
import { PANEL_WIDTH, ViewSettingsPanel } from '../components/customView/ViewSettingsPanel'
import {
  customViewPreviewUrl,
  defaultCustomViewSettings,
  neighborhoodPreset,
  sameCustomViewSettings,
  settingsToBody,
  VIEWS_LIST_PATH,
  viewPath,
  type CustomViewSettings,
} from '../lib/customView'
import {
  fieldError,
  fetchActorKinds,
  resolvePickerEntities,
  viewsApi,
  type ActorKind,
  type CustomViewFetchError,
  type PickerEntity,
  type SavedView,
} from '../lib/customViewApi'
import { draftFromSettings, draftToSettings, isDraftValid, type CustomViewDraft } from '../lib/customViewDraft'
import { failureMessage, isRenderFailure } from '../lib/customViewErrors'
import { useDiagramPreferences } from '../lib/diagramPreferences'
import { useUnsavedChangesGuard } from '../lib/useUnsavedChangesGuard'

const NARROW_QUERY = '(max-width: 900px)'
const NAME_MAX_LENGTH = 255
const DESCRIPTION_MAX_LENGTH = 4096

function useNarrowScreen(): boolean {
  const [narrow, setNarrow] = useState(() => (typeof window.matchMedia === 'function' ? window.matchMedia(NARROW_QUERY).matches : false))
  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return
    const query = window.matchMedia(NARROW_QUERY)
    const listener = () => setNarrow(query.matches)
    query.addEventListener('change', listener)
    return () => query.removeEventListener('change', listener)
  }, [])
  return narrow
}

function PreviewViewer(props: React.ComponentProps<typeof DiagramViewer>) {
  const { containerRef, height } = useFillViewportHeight()
  return <div ref={containerRef}><DiagramViewer {...props} height={height} /></div>
}

interface EditorSeed {
  name: string
  description: string
  draft: CustomViewDraft
  missingIds: string[]
  /** Settings to render right away (a saved view, or an "Open in view builder" prefill). */
  apply: CustomViewSettings | null
  notice: string | null
}

/** Whole form state as one comparable string, to tell whether anything changed since load. */
function formKey(name: string, description: string, draft: CustomViewDraft): string {
  return JSON.stringify({ name, description, settings: settingsToBody(draftToSettings(draft)) })
}

type Names = Map<string, PickerEntity>

async function seedForView(view: SavedView, actorKinds: ActorKind[], names: Names): Promise<EditorSeed> {
  const { found, missing } = await resolvePickerEntities(view.settings.entities, view.settings.level, actorKinds)
  found.forEach((entity) => names.set(entity.id, entity))
  const missingIds = [...new Set([...view.missingEntities, ...missing])]
  return {
    name: view.name,
    description: view.description,
    draft: draftFromSettings(view.settings, found),
    missingIds,
    apply: missingIds.length === 0 ? view.settings : null,
    notice: null,
  }
}

/** Derives the level from the root's kind: Systems at the Systems level, Components, Resources and APIs at the Components level. */
async function seedForRoot(rootId: string, actorKinds: ActorKind[], names: Names): Promise<EditorSeed> {
  for (const level of ['systems', 'components'] as const) {
    const { found } = await resolvePickerEntities([rootId], level, [])
    if (found.length === 0) continue
    found.forEach((entity) => names.set(entity.id, entity))
    const settings = neighborhoodPreset(level, rootId)
    return { name: '', description: '', draft: draftFromSettings(settings, found), missingIds: [], apply: settings, notice: null }
  }
  // Actor roots are not offered by the entry points, but resolve them so a hand-written link still works.
  const { found } = await resolvePickerEntities([rootId], 'systems', actorKinds)
  if (found.length > 0) {
    found.forEach((entity) => names.set(entity.id, entity))
    const settings = neighborhoodPreset('systems', rootId)
    return { name: '', description: '', draft: draftFromSettings(settings, found), missingIds: [], apply: settings, notice: null }
  }
  return {
    name: '',
    description: '',
    draft: draftFromSettings(defaultCustomViewSettings(), []),
    missingIds: [],
    apply: null,
    notice: 'The entity in this link was not found, so the view starts empty.',
  }
}

/** Create or edit a view: preview on the left, collapsible View settings on the right. */
export function ViewEditorPage() {
  const { id } = useParams()
  const [searchParams] = useSearchParams()
  const rootId = searchParams.get('root')
  const navigate = useNavigate()
  const narrow = useNarrowScreen()
  const [preferences, setPreferences] = useDiagramPreferences('custom')
  const names = useRef<Names>(new Map())

  const { data: actorKinds } = useAsync(() => fetchActorKinds().catch(() => [] as ActorKind[]), [])
  const { data: savedView, error: loadError } = useAsync<SavedView | null>(() => (id ? viewsApi.get(id) : Promise.resolve(null)), [id])
  const [seed, setSeed] = useState<EditorSeed | null>(null)
  const [seedError, setSeedError] = useState<Error | null>(null)

  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [draft, setDraft] = useState<CustomViewDraft>(() => draftFromSettings(defaultCustomViewSettings(), []))
  const [missingIds, setMissingIds] = useState<string[]>([])
  const [baseline, setBaseline] = useState('')
  const [applied, setApplied] = useState<CustomViewSettings | null>(null)
  const [displayed, setDisplayed] = useState<CustomViewSettings | null>(null)
  const [fetching, setFetching] = useState(false)
  const [fetchError, setFetchError] = useState<CustomViewFetchError | null>(null)
  const [reloadToken, setReloadToken] = useState(0)
  const [panelOpen, setPanelOpen] = useState(true)
  const [saving, setSaving] = useState(false)
  const [nameError, setNameError] = useState<string | null>(null)
  const [saveError, setSaveError] = useState<string | null>(null)

  // Seed the form once, when the saved view (edit) or the actor kinds (everything else) are known.
  const ready = actorKinds !== null && (id ? savedView !== null : true)
  useEffect(() => {
    if (!ready || seed !== null) return
    let cancelled = false
    const kinds = actorKinds ?? []
    const load = id && savedView ? seedForView(savedView, kinds, names.current) : rootId ? seedForRoot(rootId, kinds, names.current) : Promise.resolve<EditorSeed>({
      name: '', description: '', draft: draftFromSettings(defaultCustomViewSettings(), []), missingIds: [], apply: null, notice: null,
    })
    load.then((next) => {
      if (cancelled) return
      setSeed(next)
      setName(next.name)
      setDescription(next.description)
      setDraft(next.draft)
      setMissingIds(next.missingIds)
      setBaseline(formKey(next.name, next.description, next.draft))
      setApplied(next.apply)
    }).catch((error: unknown) => { if (!cancelled) setSeedError(error instanceof Error ? error : new Error(String(error))) })
    return () => { cancelled = true }
  }, [ready, seed, actorKinds, id, savedView, rootId])

  const dirty = seed !== null && formKey(name, description, draft) !== baseline
  const { dialogProps, leave, allowLeave } = useUnsavedChangesGuard(dirty)

  const draftSettings = draftToSettings(draft)
  const hasUnapplied = applied !== null && !sameCustomViewSettings(draftSettings, applied)
  const requestBody = useMemo(() => (applied ? JSON.stringify(settingsToBody(applied)) : undefined), [applied])

  const unknownFromServer = fetchError?.code === 'unknown_entity' && fetchError.entity ? [fetchError.entity] : []
  const shownMissing = [...new Set([...missingIds, ...unknownFromServer])]
  const canSave = name.trim() !== '' && isDraftValid(draft) && shownMissing.length === 0 && !saving

  function handleApply() {
    draft.entities.forEach((entity) => names.current.set(entity.id, entity))
    if (applied && sameCustomViewSettings(draftSettings, applied)) setReloadToken((value) => value + 1)
    else setApplied(draftSettings)
  }

  function handleReset() {
    if (!seed) return
    setDraft(seed.draft)
    setMissingIds(seed.missingIds)
    setFetchError(null)
  }

  async function handleSave() {
    if (!canSave) return
    setSaving(true)
    setNameError(null)
    setSaveError(null)
    try {
      const input = { name: name.trim(), description, settings: draftSettings }
      const saved = id ? await viewsApi.update(id, input) : await viewsApi.create(input)
      allowLeave()
      navigate(viewPath(saved.id))
    } catch (error) {
      const duplicate = fieldError(error, 'name')
      if (duplicate) setNameError(duplicate)
      else setSaveError(errorMessage(error, 'The view could not be saved'))
      setSaving(false)
    }
  }

  if (id && loadError) {
    const notFound = loadError instanceof ApiError && loadError.status === 404
    return (
      <section>
        <Text as="h1" variant="header-1">{notFound ? 'View not found' : 'The view could not be loaded'}</Text>
        <p><Text color="secondary">{notFound ? 'It may have been deleted.' : errorMessage(loadError)}</Text></p>
        <Button view="outlined" onClick={() => navigate(VIEWS_LIST_PATH)}>Back to views</Button>
      </section>
    )
  }
  if (seedError) return <Alert theme="danger" message={errorMessage(seedError, 'The editor could not be loaded')} />
  if (seed === null) return <Loader size="m" />

  const toggleLabel = panelOpen ? 'Hide view settings' : 'Show view settings'

  const settingsColumn = panelOpen && (
    <div style={narrow ? { width: '100%' } : { width: PANEL_WIDTH, flex: `0 0 ${PANEL_WIDTH}px` }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <ViewSettingsPanel
          draft={draft}
          onChange={setDraft}
          actorKinds={actorKinds ?? []}
          missingIds={shownMissing}
          onRemoveMissing={(missingId) => {
            setMissingIds((ids) => ids.filter((entry) => entry !== missingId))
            setFetchError(null)
            setDraft((current) => ({ ...current, entities: current.entities.filter((entity) => entity.id !== missingId) }))
          }}
          loading={fetching}
          onApply={handleApply}
          onReset={handleReset}
        />
      </div>
    </div>
  )

  const preview = (
    <section aria-labelledby="view-preview-heading" style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Text as="h2" id="view-preview-heading" variant="header-2" style={{ margin: 0 }}>View</Text>
        <Tooltip content={toggleLabel} placement="top">
          <Button size="s" view="flat" aria-label={toggleLabel} aria-expanded={panelOpen} onClick={() => setPanelOpen((open) => !open)}>
            <Icon data={panelOpen ? LayoutSideContentRight : LayoutColumns} />
          </Button>
        </Tooltip>
      </div>
      {seed.notice && <Alert theme="warning" message={seed.notice} />}
      {hasUnapplied && <Alert theme="info" message="Unapplied changes. Apply your changes to update the diagram." />}
      {fetchError && (
        <Alert
          theme="danger"
          message={failureMessage(fetchError, displayed !== null) + (fetchError.code === 'unknown_entity' ? ' Remove it from the selection to continue.' : '')}
          actions={isRenderFailure(fetchError) ? <Button view="outlined" onClick={() => setReloadToken((value) => value + 1)}>Retry</Button> : undefined}
        />
      )}
      {applied && requestBody !== undefined ? (
        <PreviewViewer
          src={customViewPreviewUrl({ rendering: preferences })}
          requestBody={requestBody}
          alt="View preview"
          fetchSource
          reloadToken={reloadToken}
          preferences={preferences}
          onPreferencesChange={setPreferences}
          onFetchingChange={(value) => { setFetching(value); if (value) setFetchError(null) }}
          onFetchError={setFetchError}
          onFetched={() => setDisplayed(applied)}
        />
      ) : (
        <div style={{ display: 'grid', placeItems: 'center', minHeight: 360, border: '1px dashed var(--g-color-line-generic)', borderRadius: 8, padding: 24, textAlign: 'center' }}>
          <Text color="secondary">Select entities and choose Apply view to build a diagram.</Text>
        </div>
      )}
    </section>
  )

  return (
    <section aria-labelledby="view-editor-heading">
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
        {id && savedView && (
          <Breadcrumbs.Item
            href={viewPath(id)}
            onClick={(event) => {
              event.preventDefault()
              void leave(viewPath(id))
            }}
          >
            {savedView.name}
          </Breadcrumbs.Item>
        )}
        <Breadcrumbs.Item>{id ? 'Edit view' : 'Create view'}</Breadcrumbs.Item>
      </Breadcrumbs>
      <HeaderActionRow
        left={<Text as="h1" id="view-editor-heading" variant="header-1" style={{ margin: 0 }}>{id ? 'Edit view' : 'Create view'}</Text>}
        right={
          <div style={{ display: 'flex', gap: 8 }}>
            <Button view="action" disabled={!canSave} loading={saving} onClick={() => void handleSave()}>Save</Button>
            <Button view="outlined" onClick={() => void leave(id ? viewPath(id) : VIEWS_LIST_PATH)}>Cancel</Button>
          </div>
        }
      />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 560 }}>
        <div>
          <Text color="secondary">Name</Text>
          <TextInput
            id="view-name"
            value={name}
            validationState={nameError ? 'invalid' : undefined}
            errorMessage={nameError ?? undefined}
            onUpdate={(value) => { setName(value); setNameError(null) }}
            controlProps={{ 'aria-label': 'Name', required: true, maxLength: NAME_MAX_LENGTH }}
          />
        </div>
        <div>
          <Text color="secondary">Description</Text>
          <TextArea
            id="view-description"
            minRows={2}
            value={description}
            onUpdate={setDescription}
            controlProps={{ 'aria-label': 'Description', maxLength: DESCRIPTION_MAX_LENGTH }}
          />
        </div>
      </div>
      {saveError && <div style={{ marginTop: 16 }}><Alert theme="danger" message={saveError} /></div>}
      <div style={{ display: 'flex', flexDirection: narrow ? 'column-reverse' : 'row', gap: 24, marginTop: 24, alignItems: narrow ? 'stretch' : 'flex-start' }}>
        {preview}
        {settingsColumn}
      </div>
      <ConfirmDialog {...dialogProps} />
    </section>
  )
}
