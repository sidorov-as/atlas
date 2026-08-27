import { useNavigate } from 'react-router-dom'
import { Icon, Label, type TableColumnConfig } from '@gravity-ui/uikit'
import { EntityListPage, ownerCell } from 'frontend/components/EntityListPage'
import { TagLabels } from 'frontend/components/TagLabels'
import { API_TYPE_THEME } from 'frontend/lib/badges'
import { apisApi } from 'frontend/lib/entities'
import { apiTypeIcon } from 'frontend/lib/icons'
import { apiRailFields } from 'frontend/lib/railFields'
import type { ApiEntity } from 'frontend/lib/types'
import { refName } from 'frontend/lib/types'

const TYPE_OPTIONS = ['openapi', 'grpc', 'asyncapi', 'graphql'].map((value) => ({ value, content: value }))

const columns: TableColumnConfig<ApiEntity>[] = [
  {
    id: 'name',
    name: 'Name',
    template: (item) => (
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <Icon data={apiTypeIcon(item.spec.type)} size={16} />
        {item.metadata.title || item.metadata.name}
      </div>
    ),
  },
  { id: 'type', name: 'Type', template: (item) => <Label theme={API_TYPE_THEME[item.spec.type]}>{item.spec.type}</Label> },
  { id: 'owner', name: 'Owner', template: ownerCell },
  { id: 'system', name: 'System', template: (item) => refName(item.spec.system) },
  { id: 'tags', name: 'Tags', template: (item) => <TagLabels tags={item.metadata.tags} tagColors={item.metadata.tagColors} /> },
]

export function ApisListPage() {
  const navigate = useNavigate()

  return (
    <EntityListPage
      title="APIs"
      description="All APIs across every system"
      addLabel="Add API"
      onAdd={() => navigate('/apis/new')}
      fetchList={apisApi.list}
      columns={columns}
      rowTo={(item) => `/apis/${item.id}`}
      railFields={apiRailFields}
      remove={apisApi.remove}
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
