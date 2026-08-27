import { useParams } from 'react-router-dom'
import { EntityDetailShell } from 'frontend/components/EntityDetailShell'
import { componentsApi } from 'frontend/lib/entities'
import { componentRailFields } from 'frontend/lib/railFields'
import { useAsync } from 'frontend/lib/useAsync'
import { composedContributions } from 'frontend/plugins/composition'

export function ComponentDetailPage() {
  const { id } = useParams()
  const componentId = id as string
  const { data: component, error, isLoading, reload } = useAsync(() => componentsApi.get(componentId), [componentId])

  if (!component) {
    return (
      <EntityDetailShell
        breadcrumb={{ label: 'Components', to: '/components' }}
        metadata={undefined}
        ingestedFrom={null}
        isLoading={isLoading}
        error={error}
        editTo=""
        railFields={[]}
        entity={undefined}
        tabContributions={composedContributions.entityDetailTabs}
      />
    )
  }

  return (
    <EntityDetailShell
      breadcrumb={{ label: 'Components', to: '/components' }}
      metadata={component.metadata}
      ingestedFrom={component.ingestedFrom}
      blockedBy={component.blockedBy}
      blockedByReason={component.blockedByReason}
      isLoading={isLoading}
      error={error}
      editTo={`/components/${component.id}/edit`}
      onRemove={async () => { await componentsApi.remove(component.id); reload() }}
      onRevive={async () => { await componentsApi.revive(component.id); reload() }}
      onPurge={() => componentsApi.purge(component.id)}
      railFields={componentRailFields(component)}
      links={component.metadata.links}
      entity={component}
      tabContributions={composedContributions.entityDetailTabs}
    />
  )
}
