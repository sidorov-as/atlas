import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Loader, Select, Text } from '@gravity-ui/uikit'
import { EntityFormShell, parseTags, type MetadataDraft } from 'frontend/components/EntityFormShell'
import { MultiRefSelect, RefSelect } from 'frontend/components/RefSelect'
import { componentsApi } from 'frontend/lib/entities'
import type { ComponentLifecycle, ComponentType } from 'frontend/lib/types'
import { useAsync } from 'frontend/lib/useAsync'

const EMPTY: MetadataDraft = { name: '', title: '', description: '', documentation: '', tags: '' }
const TYPE_OPTIONS = ['service', 'website', 'library', 'worker'].map((value) => ({ value, content: value }))
const LIFECYCLE_OPTIONS = ['experimental', 'production', 'deprecated'].map((value) => ({ value, content: value }))

export function ComponentFormPage() {
  const { id } = useParams()
  const isEdit = Boolean(id)
  const navigate = useNavigate()

  const { data: existing, isLoading } = useAsync(
    () => (isEdit ? componentsApi.get(id as string) : Promise.resolve(null)),
    [id],
  )

  const [metadata, setMetadata] = useState<MetadataDraft>(EMPTY)
  const [type, setType] = useState<ComponentType | null>(null)
  const [lifecycle, setLifecycle] = useState<ComponentLifecycle | null>(null)
  const [owner, setOwner] = useState<string | null>(null)
  const [system, setSystem] = useState<string | null>(null)
  const [providesApis, setProvidesApis] = useState<string[]>([])
  const [consumesApis, setConsumesApis] = useState<string[]>([])
  const [dependsOn, setDependsOn] = useState<string[]>([])

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
      setLifecycle(existing.spec.lifecycle)
      setOwner(existing.spec.owner)
      setSystem(existing.spec.system)
      setProvidesApis(existing.spec.providesApis)
      setConsumesApis(existing.spec.consumesApis)
      setDependsOn(existing.spec.dependsOn)
    }
  }, [existing])

  if (isEdit && isLoading && !existing) return <Loader size="l" />

  async function handleSubmit() {
    if (!type) throw new Error('Type is required')
    if (!lifecycle) throw new Error('Lifecycle is required')
    if (!owner) throw new Error('Owner is required')
    if (!system) throw new Error('System is required')
    const input = {
      metadata: { name: metadata.name, title: metadata.title, description: metadata.description, documentation: metadata.documentation, tags: parseTags(metadata.tags) },
      spec: { type, lifecycle, owner, system, providesApis, consumesApis, dependsOn },
    }
    const saved = isEdit ? await componentsApi.update(id as string, input) : await componentsApi.create(input)
    navigate(`/components/${saved.id}`)
  }

  return (
    <EntityFormShell
      breadcrumb={{ label: 'Components', to: '/components' }}
      title={isEdit ? 'Edit Component' : 'Add Component'}
      isEdit={isEdit}
      metadata={metadata}
      onMetadataChange={setMetadata}
      onSubmit={handleSubmit}
      cancelTo={isEdit ? `/components/${id}` : '/components'}
      layout="tabbed"
      specFields={
        <>
          <div>
            <Text color="secondary">Type</Text>
            <Select
              placeholder="Type"
              value={type ? [type] : []}
              onUpdate={(value) => setType((value[0] as ComponentType) ?? null)}
              options={TYPE_OPTIONS}
              width="max"
            />
          </div>
          <div>
            <Text color="secondary">Lifecycle</Text>
            <Select
              placeholder="Lifecycle"
              value={lifecycle ? [lifecycle] : []}
              onUpdate={(value) => setLifecycle((value[0] as ComponentLifecycle) ?? null)}
              options={LIFECYCLE_OPTIONS}
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
            <Text color="secondary">Provides APIs</Text>
            <MultiRefSelect kind="api" value={providesApis} onChange={setProvidesApis} placeholder="APIs provided" />
          </div>
          <div>
            <Text color="secondary">Consumes APIs</Text>
            <MultiRefSelect kind="api" value={consumesApis} onChange={setConsumesApis} placeholder="APIs consumed" />
          </div>
          <div>
            <Text color="secondary">Depends on</Text>
            <MultiRefSelect kind="resource" value={dependsOn} onChange={setDependsOn} placeholder="Resources depended on" />
          </div>
        </>
      }
    />
  )
}
