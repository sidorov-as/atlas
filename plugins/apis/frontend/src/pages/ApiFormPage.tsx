import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Button, FilePreview, Loader, SegmentedRadioGroup, Select, Text, TextInput, useFileInput } from '@gravity-ui/uikit'
import { Xmark } from '@gravity-ui/icons'
import { CodeEditor } from 'frontend/components/CodeEditor'
import { EntityFormShell, parseTags, type MetadataDraft } from 'frontend/components/EntityFormShell'
import { RefSelect } from 'frontend/components/RefSelect'
import { apisApi } from 'frontend/lib/entities'
import type { ApiSpecSource, ApiType } from 'frontend/lib/types'
import { useAsync } from 'frontend/lib/useAsync'
import { detectSpecLanguage, parseSpecContent } from '../lib/specFormat'

const EMPTY: MetadataDraft = { name: '', title: '', description: '', documentation: '', tags: '' }
const TYPE_OPTIONS = ['openapi', 'grpc', 'asyncapi', 'graphql'].map((value) => ({ value, content: value }))
const SOURCE_OPTIONS: { value: ApiSpecSource; content: string }[] = [
  { value: 'none', content: 'None' },
  { value: 'inline', content: 'Paste text' },
  { value: 'url', content: 'URL' },
]

export function ApiFormPage() {
  const { id } = useParams()
  const isEdit = Boolean(id)
  const navigate = useNavigate()

  const { data: existing, isLoading } = useAsync(() => (isEdit ? apisApi.get(id as string) : Promise.resolve(null)), [id])

  const [metadata, setMetadata] = useState<MetadataDraft>(EMPTY)
  const [type, setType] = useState<ApiType | null>(null)
  const [owner, setOwner] = useState<string | null>(null)
  const [system, setSystem] = useState<string | null>(null)
  const [specSource, setSpecSource] = useState<ApiSpecSource>('none')
  const [specUrl, setSpecUrl] = useState('')
  const [specContent, setSpecContent] = useState('')
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)

  const specParseError = useMemo(() => (specContent ? parseSpecContent(specContent) : null), [specContent])

  const { controlProps: fileControlProps, triggerProps: fileTriggerProps } = useFileInput({
    onUpdate: (files) => {
      const file = files[0]
      if (!file) return
      setUploadedFile(file)
      void file.text().then(setSpecContent)
    },
  })

  useEffect(() => {
    if (existing) {
      setMetadata({
        name: existing.metadata.name,
        title: existing.metadata.title,
        description: existing.metadata.description,
        documentation: existing.metadata.documentation,
        tags: existing.metadata.tags.join(', '),
      })
      setType(existing.spec.type)
      setOwner(existing.spec.owner)
      setSystem(existing.spec.system)
      setSpecSource(existing.spec.specSource)
      setSpecUrl(existing.spec.specUrl)
      setSpecContent(existing.spec.specContent)
    }
  }, [existing])

  if (isEdit && isLoading && !existing) return <Loader size="l" />

  async function handleSubmit() {
    if (!type) throw new Error('Type is required')
    if (!owner) throw new Error('Owner is required')
    if (!system) throw new Error('System is required')
    const input = {
      metadata: { name: metadata.name, title: metadata.title, description: metadata.description, documentation: metadata.documentation, tags: parseTags(metadata.tags) },
      spec: { type, owner, system, specSource, specUrl, specContent },
    }
    const saved = isEdit ? await apisApi.update(id as string, input) : await apisApi.create(input)
    navigate(`/apis/${saved.id}`)
  }

  return (
    <EntityFormShell
      breadcrumb={{ label: 'APIs', to: '/apis' }}
      title={isEdit ? 'Edit API' : 'Add API'}
      isEdit={isEdit}
      metadata={metadata}
      onMetadataChange={setMetadata}
      onSubmit={handleSubmit}
      cancelTo={isEdit ? `/apis/${id}` : '/apis'}
      layout="tabbed"
      specFields={
        <>
          <div>
            <Text color="secondary">Type</Text>
            <Select
              placeholder="Type"
              value={type ? [type] : []}
              onUpdate={(value) => setType((value[0] as ApiType) ?? null)}
              options={TYPE_OPTIONS}
              width="max"
            />
          </div>
          <div>
            <Text color="secondary">Owner</Text>
            <RefSelect kind="group" value={owner} onChange={setOwner} placeholder="Owning team" />
          </div>
          <div>
            <Text color="secondary">System</Text>
            <RefSelect kind="system" value={system} onChange={setSystem} placeholder="Parent system" />
          </div>
          <div>
            <Text color="secondary">Spec</Text>
            <div style={{ marginTop: 4, marginBottom: 8 }}>
              <SegmentedRadioGroup value={specSource} onUpdate={(value) => setSpecSource(value as ApiSpecSource)} options={SOURCE_OPTIONS} />
            </div>
            {specSource === 'inline' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <CodeEditor value={specContent} onChange={setSpecContent} language={detectSpecLanguage(specContent)} error={specParseError} />
                <div>
                  <input {...fileControlProps} accept=".json,.yaml,.yml,text/plain,application/json,application/yaml" />
                  <Button {...fileTriggerProps} view="outlined">
                    Upload file…
                  </Button>
                </div>
                {uploadedFile && (
                  <FilePreview file={uploadedFile} actions={[{ icon: <Xmark />, title: 'Remove', onClick: () => setUploadedFile(null) }]} />
                )}
              </div>
            )}
            {specSource === 'url' && (
              <TextInput type="url" value={specUrl} onUpdate={setSpecUrl} placeholder="https://example.com/openapi.yaml" />
            )}
          </div>
        </>
      }
    />
  )
}
