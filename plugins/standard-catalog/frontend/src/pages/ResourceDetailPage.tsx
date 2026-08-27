import { useParams } from 'react-router-dom'
import { EntityDetailShell } from 'frontend/components/EntityDetailShell'
import { resourcesApi } from 'frontend/lib/entities'
import { resourceRailFields } from 'frontend/lib/railFields'
import { useAsync } from 'frontend/lib/useAsync'
import { composedContributions } from 'frontend/plugins/composition'

export function ResourceDetailPage() {
  const { id } = useParams()
  const resourceId = id as string
  const { data: resource, error, isLoading, reload } = useAsync(() => resourcesApi.get(resourceId), [resourceId])

  if (!resource) {
    return (
      <EntityDetailShell
        breadcrumb={{ label: 'Resources', to: '/resources' }}
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
      breadcrumb={{ label: 'Resources', to: '/resources' }}
      metadata={resource.metadata}
      ingestedFrom={resource.ingestedFrom}
      blockedBy={resource.blockedBy}
      blockedByReason={resource.blockedByReason}
      isLoading={isLoading}
      error={error}
      editTo={`/resources/${resource.id}/edit`}
      onRemove={async () => { await resourcesApi.remove(resource.id); reload() }}
      onRevive={async () => { await resourcesApi.revive(resource.id); reload() }}
      onPurge={() => resourcesApi.purge(resource.id)}
      railFields={resourceRailFields(resource)}
      links={resource.metadata.links}
      entity={resource}
      tabContributions={composedContributions.entityDetailTabs}
    />
  )
}
