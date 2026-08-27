import { useParams } from 'react-router-dom'
import { EntityDetailShell } from 'frontend/components/EntityDetailShell'
import { apisApi } from 'frontend/lib/entities'
import { apiRailFields } from 'frontend/lib/railFields'
import { useAsync } from 'frontend/lib/useAsync'
import { composedContributions } from 'frontend/plugins/composition'

export function ApiDetailPage() {
  const { id } = useParams()
  const apiId = id as string
  const { data: api, error, isLoading, reload } = useAsync(() => apisApi.get(apiId), [apiId])

  if (!api) {
    return (
      <EntityDetailShell
        breadcrumb={{ label: 'APIs', to: '/apis' }}
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
      breadcrumb={{ label: 'APIs', to: '/apis' }}
      metadata={api.metadata}
      ingestedFrom={api.ingestedFrom}
      blockedBy={api.blockedBy}
      blockedByReason={api.blockedByReason}
      isLoading={isLoading}
      error={error}
      editTo={`/apis/${api.id}/edit`}
      onRemove={async () => { await apisApi.remove(api.id); reload() }}
      onRevive={async () => { await apisApi.revive(api.id); reload() }}
      onPurge={() => apisApi.purge(api.id)}
      railFields={apiRailFields(api)}
      links={api.metadata.links}
      entity={api}
      tabContributions={composedContributions.entityDetailTabs}
    />
  )
}
