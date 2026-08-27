import { useState, type FormEvent, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { Alert, Breadcrumbs, Button, Tab, TabList, TabPanel, TabProvider, Text, TextArea, TextInput } from '@gravity-ui/uikit'
import { DocumentationEditor } from './DocumentationEditor'
import { HeaderActionRow } from './HeaderActionRow'

export interface MetadataDraft {
  name: string
  title: string
  description: string
  documentation: string
  tags: string
}

interface EntityFormShellProps {
  breadcrumb: { label: string; to: string }
  title: string
  isEdit: boolean
  metadata: MetadataDraft
  onMetadataChange: (metadata: MetadataDraft) => void
  specFields: ReactNode
  onSubmit: () => Promise<void>
  cancelTo: string
  /** `'tabbed'` splits the body into an Overview tab (fields) and a Documentation tab (the Markdown editor, unconstrained width) — Component/API opt in; everything else keeps `'single'` (default), unchanged aside from the header move. */
  layout?: 'single' | 'tabbed'
}

/** Name/title/description/tags fields + spec-field slot + save/cancel, shared by every entity form. */
export function EntityFormShell({
  breadcrumb,
  title,
  isEdit,
  metadata,
  onMetadataChange,
  specFields,
  onSubmit,
  cancelTo,
  layout = 'single',
}: EntityFormShellProps) {
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [nameTouched, setNameTouched] = useState(false)
  const [activeTab, setActiveTab] = useState('overview')

  const nameInvalid = nameTouched && !metadata.name.trim()

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setNameTouched(true)
    if (!metadata.name.trim()) {
      // The Name field only renders on the Overview tab — switch there so the inline
      // `errorMessage` this sets is actually visible, even when submit was triggered from
      // the Documentation tab (mirrors FlowFormPage.handleSubmit).
      if (layout === 'tabbed') setActiveTab('overview')
      return
    }
    setIsSaving(true)
    try {
      await onSubmit()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setIsSaving(false)
    }
  }

  const overviewFields = (
    <>
      <div>
        <Text color="secondary">Name</Text>
        <TextInput
          value={metadata.name}
          onUpdate={(name) => onMetadataChange({ ...metadata, name })}
          onBlur={() => setNameTouched(true)}
          disabled={isEdit}
          placeholder="my-system"
          validationState={nameInvalid ? 'invalid' : undefined}
          errorMessage={nameInvalid ? 'Name is required' : undefined}
        />
      </div>
      <div>
        <Text color="secondary">Title</Text>
        <TextInput value={metadata.title} onUpdate={(value) => onMetadataChange({ ...metadata, title: value })} />
      </div>
      <div>
        <Text color="secondary">Description</Text>
        <TextArea
          value={metadata.description}
          onUpdate={(value) => onMetadataChange({ ...metadata, description: value })}
          minRows={2}
        />
      </div>
      <div>
        <Text color="secondary">Tags (comma-separated)</Text>
        <TextInput value={metadata.tags} onUpdate={(value) => onMetadataChange({ ...metadata, tags: value })} />
      </div>
      {specFields}
    </>
  )

  const documentationField = (
    <div>
      <Text color="secondary">Documentation</Text>
      <DocumentationEditor
        value={metadata.documentation}
        onChange={(documentation) => onMetadataChange({ ...metadata, documentation })}
      />
    </div>
  )

  // On edit, `cancelTo` is the entity's own detail page — reused here so the entity crumb
  // matches where Cancel goes. Held back until a name is loaded so the loading state doesn't
  // flash a blank crumb.
  const entityLabel = metadata.title || metadata.name
  const entityCrumb = isEdit && entityLabel ? { label: entityLabel, to: cancelTo } : null

  return (
    <div>
      <Breadcrumbs>
        <Breadcrumbs.Item
          href={breadcrumb.to}
          onClick={(event) => {
            event.preventDefault()
            navigate(breadcrumb.to)
          }}
        >
          {breadcrumb.label}
        </Breadcrumbs.Item>
        {entityCrumb && (
          <Breadcrumbs.Item
            href={entityCrumb.to}
            onClick={(event) => {
              event.preventDefault()
              navigate(entityCrumb.to)
            }}
          >
            {entityCrumb.label}
          </Breadcrumbs.Item>
        )}
        <Breadcrumbs.Item>{title}</Breadcrumbs.Item>
      </Breadcrumbs>

      <form onSubmit={(event) => void handleSubmit(event)}>
        <HeaderActionRow
          left={<Text variant="header-1">{title}</Text>}
          right={
            <div style={{ display: 'flex', gap: 8 }}>
              <Button view="action" type="submit" loading={isSaving}>
                {isEdit ? 'Save' : 'Create'}
              </Button>
              <Button view="outlined" onClick={() => navigate(cancelTo)}>
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
        {layout === 'tabbed' ? (
          <TabProvider value={activeTab} onUpdate={setActiveTab}>
            <TabList>
              <Tab value="overview">Overview</Tab>
              <Tab value="documentation">Documentation</Tab>
            </TabList>
            {activeTab === 'documentation' ? (
              <TabPanel value="documentation">
                <div style={{ paddingTop: 16 }}>{documentationField}</div>
              </TabPanel>
            ) : (
              <TabPanel value="overview">
                <div style={{ maxWidth: 560, display: 'flex', flexDirection: 'column', gap: 16, paddingTop: 16 }}>
                  {overviewFields}
                </div>
              </TabPanel>
            )}
          </TabProvider>
        ) : (
          <div style={{ maxWidth: 560, display: 'flex', flexDirection: 'column', gap: 16 }}>
            {overviewFields}
            {documentationField}
          </div>
        )}
      </form>
    </div>
  )
}

export function parseTags(value: string): string[] {
  return value
    .split(',')
    .map((tag) => tag.trim())
    .filter(Boolean)
}
