import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Loader, Select, Text } from '@gravity-ui/uikit'
import { EntityFormShell, parseTags, type MetadataDraft } from 'frontend/components/EntityFormShell'
import { RefSelect } from 'frontend/components/RefSelect'
import { resourcesApi } from 'frontend/lib/entities'
import type { ResourceType } from 'frontend/lib/types'
import { useAsync } from 'frontend/lib/useAsync'

const EMPTY: MetadataDraft = { name: '', title: '', description: '', documentation: '', tags: '' }
const TYPE_OPTIONS = ['database', 'cache', 'bucket', 'queue', 'cluster'].map((value) => ({ value, content: value }))

export function ResourceFormPage() {
  const { id } = useParams()
  const isEdit = Boolean(id)
  const navigate = useNavigate()

  const { data: existing, isLoading } = useAsync(
    () => (isEdit ? resourcesApi.get(id as string) : Promise.resolve(null)),
    [id],
  )

  const [metadata, setMetadata] = useState<MetadataDraft>(EMPTY)
  const [type, setType] = useState<ResourceType | null>(null)
  const [owner, setOwner] = useState<string | null>(null)
  const [system, setSystem] = useState<string | null>(null)

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
    }
  }, [existing])

  if (isEdit && isLoading && !existing) return <Loader size="l" />

  async function handleSubmit() {
    if (!type) throw new Error('Type is required')
    if (!owner) throw new Error('Owner is required')
    const input = {
      metadata: { name: metadata.name, title: metadata.title, description: metadata.description, documentation: metadata.documentation, tags: parseTags(metadata.tags) },
      spec: { type, owner, system },
    }
    const saved = isEdit ? await resourcesApi.update(id as string, input) : await resourcesApi.create(input)
    navigate(`/resources/${saved.id}`)
  }

  return (
    <EntityFormShell
      breadcrumb={{ label: 'Resources', to: '/resources' }}
      title={isEdit ? 'Edit Resource' : 'Add Resource'}
      isEdit={isEdit}
      metadata={metadata}
      onMetadataChange={setMetadata}
      onSubmit={handleSubmit}
      cancelTo={isEdit ? `/resources/${id}` : '/resources'}
      specFields={
        <>
          <div>
            <Text color="secondary">Type</Text>
            <Select
              placeholder="Type"
              value={type ? [type] : []}
              onUpdate={(value) => setType((value[0] as ResourceType) ?? null)}
              options={TYPE_OPTIONS}
              width="max"
            />
          </div>
          <div>
            <Text color="secondary">Owner</Text>
            <RefSelect kind="group" value={owner} onChange={setOwner} placeholder="Owning team" />
          </div>
          <div>
            <Text color="secondary">System (optional)</Text>
            <RefSelect kind="system" value={system} onChange={setSystem} placeholder="Parent system" allowEmpty />
          </div>
        </>
      }
    />
  )
}
