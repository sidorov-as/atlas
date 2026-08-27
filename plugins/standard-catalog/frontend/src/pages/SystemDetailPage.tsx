import { useParams } from 'react-router-dom'
import { EntityDetailShell } from 'frontend/components/EntityDetailShell'
import { systemsApi } from 'frontend/lib/entities'
import { systemRailFields } from 'frontend/lib/railFields'
import { useAsync } from 'frontend/lib/useAsync'
import { composedContributions } from 'frontend/plugins/composition'

export function SystemDetailPage() {
  const { id } = useParams()
  const systemId = id as string
  const { data: system, error, isLoading, reload } = useAsync(() => systemsApi.get(systemId), [systemId])
  if (!system) {
    return (
      <EntityDetailShell
        breadcrumb={{ label: 'Systems', to: '/systems' }}
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
      breadcrumb={{ label: 'Systems', to: '/systems' }}
      metadata={system.metadata}
      ingestedFrom={system.ingestedFrom}
      blockedBy={system.blockedBy}
      blockedByReason={system.blockedByReason}
      isLoading={isLoading}
      error={error}
      editTo={`/systems/${system.id}/edit`}
      onRemove={async () => { await systemsApi.remove(system.id); reload() }}
      onRevive={async () => { await systemsApi.revive(system.id); reload() }}
      onPurge={() => systemsApi.purge(system.id)}
      railFields={systemRailFields(system)}
      links={system.metadata.links}
      entity={system}
      tabContributions={composedContributions.entityDetailTabs}
    />
  )
}
