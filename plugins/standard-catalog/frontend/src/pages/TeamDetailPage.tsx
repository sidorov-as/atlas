import { useParams } from 'react-router-dom'
import { EntityDetailShell } from 'frontend/components/EntityDetailShell'
import { groupsApi } from 'frontend/lib/entities'
import { teamRailFields } from 'frontend/lib/railFields'
import { useAsync } from 'frontend/lib/useAsync'
import { composedContributions } from 'frontend/plugins/composition'

/** Groups have no edit/delete route in this app — managed entirely via Django admin (see TeamsListPage). */
export function TeamDetailPage() {
  const { id } = useParams()
  const groupId = id as string
  const { data: group, error, isLoading } = useAsync(() => groupsApi.get(groupId), [groupId])

  if (!group) {
    return (
      <EntityDetailShell
        breadcrumb={{ label: 'Teams', to: '/teams' }}
        metadata={undefined}
        ingestedFrom={null}
        isLoading={isLoading}
        error={error}
        editTo=""
        editable={false}
        railFields={[]}
        entity={undefined}
        tabContributions={composedContributions.entityDetailTabs}
      />
    )
  }

  return (
    <EntityDetailShell
      breadcrumb={{ label: 'Teams', to: '/teams' }}
      metadata={group.metadata}
      ingestedFrom={null}
      isLoading={isLoading}
      error={error}
      editTo=""
      editable={false}
      railFields={teamRailFields(group)}
      links={group.metadata.links}
      entity={group}
      tabContributions={composedContributions.entityDetailTabs}
    />
  )
}
