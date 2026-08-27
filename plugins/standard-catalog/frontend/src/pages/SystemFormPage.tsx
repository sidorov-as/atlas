import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Loader, Text } from '@gravity-ui/uikit'
import { EntityFormShell, parseTags, type MetadataDraft } from 'frontend/components/EntityFormShell'
import { RefSelect } from 'frontend/components/RefSelect'
import { systemsApi } from 'frontend/lib/entities'
import { useAsync } from 'frontend/lib/useAsync'

const EMPTY: MetadataDraft = { name: '', title: '', description: '', documentation: '', tags: '' }

export function SystemFormPage() {
  const { id } = useParams()
  const isEdit = Boolean(id)
  const navigate = useNavigate()

  const { data: existing, isLoading } = useAsync(
    () => (isEdit ? systemsApi.get(id as string) : Promise.resolve(null)),
    [id],
  )

  const [metadata, setMetadata] = useState<MetadataDraft>(EMPTY)
  const [owner, setOwner] = useState<string | null>(null)

  useEffect(() => {
    if (existing) {
      setMetadata({
        name: existing.metadata.name,
        title: existing.metadata.title,
        description: existing.metadata.description,
        documentation: existing.metadata.documentation,
        tags: existing.metadata.tags.join(', '),
      })
      setOwner(existing.spec.owner)
    }
  }, [existing])

  if (isEdit && isLoading && !existing) return <Loader size="l" />
  if (existing?.ingestedFrom) return <Text color="secondary">This System is managed by catalog-info.yaml and cannot be edited here.</Text>

  async function handleSubmit() {
    if (!owner) throw new Error('Owner is required')
    const input = {
      metadata: { name: metadata.name, title: metadata.title, description: metadata.description, documentation: metadata.documentation, tags: parseTags(metadata.tags) },
      spec: { owner },
    }
    const saved = isEdit ? await systemsApi.update(id as string, input) : await systemsApi.create(input)
    navigate(`/systems/${saved.id}`)
  }

  return (
    <EntityFormShell
      breadcrumb={{ label: 'Systems', to: '/systems' }}
      title={isEdit ? 'Edit System' : 'Add System'}
      isEdit={isEdit}
      metadata={metadata}
      onMetadataChange={setMetadata}
      onSubmit={handleSubmit}
      cancelTo={isEdit ? `/systems/${id}` : '/systems'}
      specFields={
        <div>
          <Text color="secondary">Owner</Text>
          <RefSelect kind="group" value={owner} onChange={setOwner} placeholder="Owning team" />
        </div>
      }
    />
  )
}
