import { useNavigate } from 'react-router-dom'
import { Icon, Label, type TableColumnConfig } from '@gravity-ui/uikit'
import { EntityListPage, ownerCell } from 'frontend/components/EntityListPage'
import { TagLabels } from 'frontend/components/TagLabels'
import { RESOURCE_TYPE_THEME } from 'frontend/lib/badges'
import { resourcesApi } from 'frontend/lib/entities'
import { resourceTypeIcon } from 'frontend/lib/icons'
import { resourceRailFields } from 'frontend/lib/railFields'
import type { ResourceEntity } from 'frontend/lib/types'
import { refName } from 'frontend/lib/types'

const TYPE_OPTIONS = ['database', 'cache', 'bucket', 'queue', 'cluster'].map((value) => ({
  value,
  content: value,
}))

const columns: TableColumnConfig<ResourceEntity>[] = [
  {
    id: 'name',
    name: 'Name',
    template: (item) => (
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <Icon data={resourceTypeIcon(item.spec.type)} size={16} />
        {item.metadata.title || item.metadata.name}
      </div>
    ),
  },
  { id: 'type', name: 'Type', template: (item) => <Label theme={RESOURCE_TYPE_THEME[item.spec.type]}>{item.spec.type}</Label> },
  { id: 'owner', name: 'Owner', template: ownerCell },
  { id: 'system', name: 'System', template: (item) => refName(item.spec.system) || '—' },
  { id: 'tags', name: 'Tags', template: (item) => <TagLabels tags={item.metadata.tags} tagColors={item.metadata.tagColors} /> },
]

export function ResourcesListPage() {
  const navigate = useNavigate()

  return (
    <EntityListPage
      title="Resources"
      description="All resources across every system"
      addLabel="Add Resource"
      onAdd={() => navigate('/resources/new')}
      fetchList={resourcesApi.list}
      columns={columns}
      rowTo={(item) => `/resources/${item.id}`}
      railFields={resourceRailFields}
      remove={resourcesApi.remove}
      extraFilters={(setFilter, values) => [
        {
          label: 'Type',
          value: values.type ?? null,
          onChange: (value) => setFilter('type', value),
          options: TYPE_OPTIONS,
        },
      ]}
    />
  )
}
