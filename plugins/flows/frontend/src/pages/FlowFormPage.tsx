import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { Alert, Breadcrumbs, Button, Icon, Loader, Tab, TabList, TabPanel, TabProvider, Text, TextArea, TextInput, Tooltip } from '@gravity-ui/uikit'
import { LayoutColumns, LayoutSideContentRight, Plus } from '@gravity-ui/icons'
import { Editor, type Monaco, type OnMount, type OnValidate } from '@monaco-editor/react'
import { FlowCanvasEditor } from '../components/FlowCanvasEditor'
import { FlowStepModal } from '../components/FlowStepModal'
import { DocumentationEditor } from 'frontend/components/DocumentationEditor'
import { HeaderActionRow } from 'frontend/components/HeaderActionRow'
import { RefSelect } from 'frontend/components/RefSelect'
import { errorMessage } from 'frontend/lib/api'
import { flowsApi } from 'frontend/lib/entities'
import { FlowEntityCatalogProvider } from '../lib/flowEntityCatalog'
import { flowStepSchema, FLOW_STEP_SCHEMA_URI } from '../lib/flowStepSchema'
import { parseFlowSteps, serializeFlowSteps, validateFlowSteps } from '../components/flowSteps'
import { nextRowPosition, type FlowLayoutDirection, type FlowLayoutEngine, type FlowPositions } from '../lib/flowLayout'
import { activeFlowTheme, defineFlowThemes, findStepRange } from '../lib/monacoFlowTheme'
import { useFillViewportHeight } from 'frontend/lib/useFillViewportHeight'
import type { FlowStep, FlowStepRefStatus } from 'frontend/lib/types'
import { useAsync } from 'frontend/lib/useAsync'

// monaco.MarkerSeverity.Error — kept as a literal so this file doesn't need a
// value import of the `monaco-editor` namespace just for one enum member.
const MONACO_ERROR_SEVERITY = 8

function handleEditorBeforeMount(monaco: Monaco) {
  defineFlowThemes(monaco)
  monaco.languages.json.jsonDefaults.setDiagnosticsOptions({
    validate: true,
    schemaValidation: 'error',
    schemas: [{ uri: FLOW_STEP_SCHEMA_URI, fileMatch: ['*'], schema: flowStepSchema }],
  })
}

interface FlowStepsPanelProps {
  steps: FlowStep[]
  refStatus?: Record<string, FlowStepRefStatus>
  onChange: (steps: FlowStep[]) => void
  autolayoutEnabled: boolean
  layoutDirection: FlowLayoutDirection
  layoutEngine: FlowLayoutEngine
  onAutolayoutEnabledChange: (enabled: boolean) => void
  onLayoutEngineChange: (engine: FlowLayoutEngine) => void
  onEditStep: (stepId: string) => void
  fitViewStepId: string | null
  onPositionsChange: (positions: FlowPositions) => void
  onAddStep: () => void
  isEditorOpen: boolean
  onToggleEditor: () => void
  stepsText: string
  onStepsTextChange: (value: string) => void
  jsonError: string | null
  monacoError: string | null
  structuralError: string | null
  onEditorMount: OnMount
  onEditorValidate: OnValidate
}

/** Fills the Flow tab down to the bottom of the viewport, same as `FlowDetailPage`'s Flow tab — both the canvas and the JSON rail share that one measured height, instead of the JSON rail's old fixed height. Lives in its own component so the fill-viewport measurement remounts each time the Flow tab becomes active (see `useFillViewportHeight`'s doc comment). */
function FlowStepsPanel({
  steps,
  refStatus,
  onChange,
  autolayoutEnabled,
  layoutDirection,
  layoutEngine,
  onAutolayoutEnabledChange,
  onLayoutEngineChange,
  onEditStep,
  fitViewStepId,
  onPositionsChange,
  onAddStep,
  isEditorOpen,
  onToggleEditor,
  stepsText,
  onStepsTextChange,
  jsonError,
  monacoError,
  structuralError,
  onEditorMount,
  onEditorValidate,
}: FlowStepsPanelProps) {
  const { containerRef, height } = useFillViewportHeight()

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
        <Text color="secondary">Steps</Text>
        <div style={{ display: 'flex', gap: 8 }}>
          <Button size="s" onClick={onAddStep}>
            <Icon data={Plus} /> Add Step
          </Button>
          <Tooltip content={isEditorOpen ? 'Hide JSON' : 'Show JSON'} placement="top">
            <Button
              size="s"
              view="flat"
              aria-label={isEditorOpen ? 'Hide JSON' : 'Show JSON'}
              onClick={onToggleEditor}
            >
              <Icon data={isEditorOpen ? LayoutSideContentRight : LayoutColumns} />
            </Button>
          </Tooltip>
        </div>
      </div>
      <div ref={containerRef} style={{ display: 'flex', gap: 16 }}>
        <div style={{ flex: '3 1 0', minWidth: 0, border: '1px solid var(--g-color-line-generic)', borderRadius: 8 }}>
          <FlowCanvasEditor
            steps={steps}
            refStatus={refStatus}
            onChange={onChange}
            autolayoutEnabled={autolayoutEnabled}
            layoutDirection={layoutDirection}
            layoutEngine={layoutEngine}
            onAutolayoutEnabledChange={onAutolayoutEnabledChange}
            onLayoutEngineChange={onLayoutEngineChange}
            onEditStep={onEditStep}
            fitViewStepId={fitViewStepId}
            onPositionsChange={onPositionsChange}
            height={height}
          />
        </div>

        {isEditorOpen && (
          <div style={{ flex: '1 1 0', minWidth: 280, display: 'flex', flexDirection: 'column', gap: 8 }}>
            <Editor
              height={height}
              language="json"
              value={stepsText}
              theme={activeFlowTheme()}
              beforeMount={handleEditorBeforeMount}
              onMount={onEditorMount}
              onChange={(value) => onStepsTextChange(value ?? '')}
              onValidate={onEditorValidate}
              options={{ minimap: { enabled: false }, automaticLayout: true, scrollBeyondLastLine: false, tabSize: 2 }}
            />
            {jsonError && (
              <Text color="danger" style={{ display: 'block' }}>
                {jsonError}
              </Text>
            )}
            {monacoError && (
              <Text color="danger" style={{ display: 'block' }}>
                {monacoError}
              </Text>
            )}
            {structuralError && (
              <Text color="danger" style={{ display: 'block' }}>
                {structuralError}
              </Text>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

/** Create/edit Flow: General tab holds name/description/system/documentation, Flow tab is a full-screen `FlowCanvasEditor` with an optional JSON rail kept in sync onto the same `steps`. */
export function FlowFormPage() {
  const { id } = useParams()
  const isEdit = Boolean(id)
  const navigate = useNavigate()
  const location = useLocation()

  const { data: existing, isLoading } = useAsync(
    () => (isEdit ? flowsApi.get(Number(id)) : Promise.resolve(null)),
    [id],
  )

  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [documentation, setDocumentation] = useState('')
  const [system, setSystem] = useState<string | null>(null)
  const [stepsText, setStepsText] = useState('[]')
  const [steps, setSteps] = useState<FlowStep[]>([])
  // Persisted, Flow-level fields — sourced from the Flow being edited, defaulting to autolayout-on/
  // left-right for a new one, same as the backend model's own field defaults.
  const [autolayoutEnabled, setAutolayoutEnabled] = useState(true)
  const [layoutDirection, setLayoutDirection] = useState<FlowLayoutDirection>('LAYOUT_LEFT_RIGHT')
  const [layoutEngine, setLayoutEngine] = useState<FlowLayoutEngine>('dagre')
  const [canvasFitViewStepId, setCanvasFitViewStepId] = useState<string | null>(null)
  const resolvedPositionsRef = useRef<FlowPositions>({})
  const [error, setError] = useState<string | null>(null)
  const [monacoError, setMonacoError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [isEditorOpen, setIsEditorOpen] = useState(false)
  const [nameTouched, setNameTouched] = useState(false)
  // Mirrors whichever tab the Detail page's Edit button was clicked from
  // (`FlowDetailPage`'s "flow" tab -> here's "flow", everything else,
  // including a direct URL visit with no navigation state, -> "general") so
  // opening the canvas editor doesn't cost an extra click every time.
  const [activeTab, setActiveTab] = useState(() => (
    (location.state as { fromTab?: string } | null)?.fromTab === 'flow' ? 'flow' : 'general'
  ))
  const [stepModal, setStepModal] = useState<{ mode: 'add' } | { mode: 'edit'; stepId: string } | null>(null)
  const editorRef = useRef<Parameters<OnMount>[0] | null>(null)

  useEffect(() => {
    if (existing) {
      setName(existing.name)
      setDescription(existing.description)
      setDocumentation(existing.documentation)
      setSystem(existing.system)
      setSteps(existing.steps)
      setStepsText(serializeFlowSteps(existing.steps))
      setAutolayoutEnabled(existing.autolayoutEnabled)
      setLayoutDirection(existing.layoutDirection)
      setLayoutEngine(existing.layoutEngine)
    }
  }, [existing])

  const { steps: parsedSteps, error: jsonError } = useMemo(() => parseFlowSteps(stepsText), [stepsText])
  // Computed on the freshly-parsed candidate, not the already-committed `steps` below —
  // this is what lets the sync effect reject a structurally broken edit *before* it ever
  // reaches the canvas, instead of only catching it at Save.
  const parsedStructuralErrors = useMemo(() => (parsedSteps ? validateFlowSteps(parsedSteps) : []), [parsedSteps])
  // Save-time backstop over the already-committed `steps` — normally unreachable now that the
  // sync effect below never lets a structurally invalid `parsedSteps` become `steps` in the
  // first place, but kept so `handleSubmit` still refuses to save if `steps` somehow ends up
  // invalid some other way (e.g. a canvas-driven edit this gate doesn't cover).
  const structuralErrors = useMemo(() => validateFlowSteps(steps), [steps])
  // Only shown once the JSON itself parses and shape-validates — `jsonError` already covers
  // that case, so this never doubles up with it.
  const structuralError = !jsonError && parsedStructuralErrors.length > 0 ? parsedStructuralErrors[0] : null

  const nameInvalid = nameTouched && !name.trim()

  // JSON edits flow into the canvas whenever they parse successfully *and* are structurally
  // valid, whether or not the JSON rail is open — the canvas is the only editable view, JSON
  // is just an optional rail onto the same `steps`. While either check
  // fails, the canvas keeps rendering its last good `steps` and the rail shows the specific
  // error inline instead of committing a broken diagram silently.
  useEffect(() => {
    if (parsedSteps && parsedStructuralErrors.length === 0) setSteps(parsedSteps)
  }, [parsedSteps, parsedStructuralErrors])

  function updateVisualSteps(next: FlowStep[]) {
    setSteps(next)
    setStepsText(serializeFlowSteps(next))
  }

  if (isEdit && isLoading && !existing) return <Loader size="l" />

  function handleEditorMount(editor: Parameters<OnMount>[0]) {
    editorRef.current = editor
  }

  function handleEditorValidate(markers: Parameters<OnValidate>[0]) {
    const firstError = markers.find((marker) => marker.severity === MONACO_ERROR_SEVERITY)
    setMonacoError(firstError ? `${firstError.message} (line ${firstError.startLineNumber})` : null)
  }

  /** Scrolls the JSON rail to and selects the given step's block, when the rail is open. */
  function scrollToStep(stepId: string) {
    if (!isEditorOpen) return
    const editor = editorRef.current
    const model = editor?.getModel()
    if (!editor || !model) return
    const range = findStepRange(model.getValue(), stepId)
    if (!range) return
    const start = model.getPositionAt(range.start)
    const end = model.getPositionAt(range.end)
    editor.revealLinesInCenter(start.lineNumber, end.lineNumber)
    editor.setSelection({
      startLineNumber: start.lineNumber,
      startColumn: start.column,
      endLineNumber: end.lineNumber,
      endColumn: end.column,
    })
    editor.focus()
  }

  /** Canvas node click: opens the edit modal, and — if the JSON rail is open — also scrolls to the step's block. A node's own `↻` control no longer routes here — it applies directly in `FlowCanvasEditor`. */
  function handleEditStep(stepId: string) {
    setStepModal({ mode: 'edit', stepId })
    scrollToStep(stepId)
  }

  /** "Add Step" always opens `FlowStepModal`'s node-type picker — the canvas is the only editable surface now. */
  function handleAddStep() {
    setStepModal({ mode: 'add' })
  }

  /** Saves the Add/Edit modal's step, cascading an id rename onto any transition that targeted the old id. */
  function handleStepModalSave(nextStep: FlowStep, previousId: string | null) {
    if (previousId === null) {
      // Deterministic, non-colliding placement for the toolbar-add path
      // a new row below the flow's
      // existing bounding box, read from the canvas's own merged
      // (stored-or-autolayout) positions rather than recomputed here.
      const position = nextRowPosition(steps, resolvedPositionsRef.current)
      const placedStep = { ...nextStep, position }
      updateVisualSteps([...steps, placedStep])
      setCanvasFitViewStepId(placedStep.id)
    } else {
      updateVisualSteps(steps.map((step) => {
        if (step.id === previousId) return nextStep
        if (previousId === nextStep.id) return step
        return {
          ...step,
          next_step: step.next_step?.id === previousId ? { ...step.next_step, id: nextStep.id } : step.next_step,
          next_steps: step.next_steps?.map((transition) => transition.id === previousId ? { ...transition, id: nextStep.id } : transition),
        }
      }))
    }
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setNameTouched(true)
    if (!name.trim()) {
      // The Name field only renders on the General tab (see the tab-conditional
      // render below) — switch there so the inline `errorMessage` this sets is
      // actually visible, even when submit was triggered from the Flow tab.
      setActiveTab('general')
      return
    }
    if (!system) {
      setError('System is required')
      return
    }
    if (isEditorOpen && jsonError) {
      setError(`Steps: ${jsonError}`)
      return
    }
    if (structuralErrors.length > 0) {
      setError(`Steps: ${structuralErrors[0]}`)
      return
    }
    setIsSaving(true)
    try {
      const input = { system, name, description, documentation, steps, autolayoutEnabled, layoutDirection, layoutEngine }
      const saved = isEdit ? await flowsApi.update(Number(id), input) : await flowsApi.create(input)
      navigate(`/flows/${saved.id}`)
    } catch (err) {
      setError(errorMessage(err, 'Save failed'))
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div>
      {/* Provided once here, above both `FlowStepModal` mount points (this page's own, right
          below, and `FlowCanvasEditor`'s own inside `FlowStepsPanel`) — one fetch per page
          visit shared by both. */}
      <FlowEntityCatalogProvider>
        <Breadcrumbs>
          <Breadcrumbs.Item
            href="/flows"
            onClick={(event) => {
              event.preventDefault()
              navigate('/flows')
            }}
          >
            Flows
          </Breadcrumbs.Item>
          {isEdit && name && (
            <Breadcrumbs.Item
              href={`/flows/${id}`}
              onClick={(event) => {
                event.preventDefault()
                navigate(`/flows/${id}`)
              }}
            >
              {name}
            </Breadcrumbs.Item>
          )}
          <Breadcrumbs.Item>{isEdit ? 'Edit Flow' : 'Add Flow'}</Breadcrumbs.Item>
        </Breadcrumbs>

        <form onSubmit={(event) => void handleSubmit(event)}>
          <HeaderActionRow
            left={<Text variant="header-1">{isEdit ? 'Edit Flow' : 'Add Flow'}</Text>}
            right={
              <div style={{ display: 'flex', gap: 8 }}>
                <Button view="action" type="submit" loading={isSaving}>
                  {isEdit ? 'Save' : 'Create'}
                </Button>
                <Button view="outlined" onClick={() => navigate(isEdit ? `/flows/${id}` : '/flows')}>
                  Cancel
                </Button>
              </div>
            }
          />
          {error && (
            <div style={{ marginBottom: 16 }}>
              <Alert theme="danger" message={error} />
            </div>
          )}

          <TabProvider value={activeTab} onUpdate={setActiveTab}>
            <TabList>
              <Tab value="general">General</Tab>
              <Tab value="flow">Flow</Tab>
            </TabList>

            {activeTab === 'flow' ? (
              <TabPanel value="flow">
                <div style={{ paddingTop: 16 }}>
                  <FlowStepsPanel
                    steps={steps}
                    refStatus={existing?.refStatus}
                    onChange={updateVisualSteps}
                    autolayoutEnabled={autolayoutEnabled}
                    layoutDirection={layoutDirection}
                    layoutEngine={layoutEngine}
                    onAutolayoutEnabledChange={setAutolayoutEnabled}
                    onLayoutEngineChange={setLayoutEngine}
                    onEditStep={handleEditStep}
                    fitViewStepId={canvasFitViewStepId}
                    onPositionsChange={(positions) => { resolvedPositionsRef.current = positions }}
                    onAddStep={handleAddStep}
                    isEditorOpen={isEditorOpen}
                    onToggleEditor={() => setIsEditorOpen((open) => !open)}
                    stepsText={stepsText}
                    onStepsTextChange={setStepsText}
                    jsonError={jsonError}
                    monacoError={monacoError}
                    structuralError={structuralError}
                    onEditorMount={handleEditorMount}
                    onEditorValidate={handleEditorValidate}
                  />
                </div>
              </TabPanel>
            ) : (
              <TabPanel value="general">
                <div style={{ paddingTop: 16, display: 'flex', gap: 32, alignItems: 'flex-start', flexWrap: 'wrap' }}>
                  <div style={{ flex: '0 0 300px', display: 'flex', flexDirection: 'column', gap: 16 }}>
                    <div>
                      <Text color="secondary">Name</Text>
                      <TextInput
                        value={name}
                        onUpdate={setName}
                        onBlur={() => setNameTouched(true)}
                        disabled={isEdit}
                        placeholder="checkout-saga"
                        validationState={nameInvalid ? 'invalid' : undefined}
                        errorMessage={nameInvalid ? 'Name is required' : undefined}
                      />
                    </div>
                    <div>
                      <Text color="secondary">Description</Text>
                      <TextArea value={description} onUpdate={setDescription} minRows={2} />
                    </div>
                    <div>
                      <Text color="secondary">System</Text>
                      <RefSelect kind="system" value={system} onChange={setSystem} placeholder="Home system" />
                    </div>
                  </div>

                  <div style={{ flex: '1 1 100%', minWidth: 0 }}>
                    <Text color="secondary">Documentation</Text>
                    <DocumentationEditor value={documentation} onChange={setDocumentation} />
                  </div>
                </div>
              </TabPanel>
            )}
          </TabProvider>
        </form>
        <FlowStepModal
          open={stepModal !== null}
          steps={steps}
          step={stepModal?.mode === 'edit' ? steps.find((step) => step.id === stepModal.stepId) ?? null : null}
          refStatus={stepModal?.mode === 'edit' ? existing?.refStatus?.[stepModal.stepId] : undefined}
          onClose={() => setStepModal(null)}
          onSave={handleStepModalSave}
        />
      </FlowEntityCatalogProvider>
    </div>
  )
}
