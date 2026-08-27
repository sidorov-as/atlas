import { useNavigate } from 'react-router-dom'
import { Icon, Label, type TableColumnConfig } from '@gravity-ui/uikit'
import { EntityListPage, ownerCell } from 'frontend/components/EntityListPage'
import { TagLabels } from 'frontend/components/TagLabels'
import { COMPONENT_TYPE_THEME, LIFECYCLE_THEME } from 'frontend/lib/badges'
import { componentsApi } from 'frontend/lib/entities'
import { componentTypeIcon } from 'frontend/lib/icons'
import { componentRailFields } from 'frontend/lib/railFields'
import type { ComponentEntity } from 'frontend/lib/types'
import { refName } from 'frontend/lib/types'

const TYPE_OPTIONS = ['service', 'website', 'library', 'worker'].map((value) => ({ value, content: value }))
const LIFECYCLE_OPTIONS = ['experimental', 'production', 'deprecated'].map((value) => ({ value, content: value }))

const columns: TableColumnConfig<ComponentEntity>[] = [
  {
    id: 'name',
    name: 'Name',
    template: (item) => (
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <Icon data={componentTypeIcon(item.spec.type)} size={16} />
        {item.metadata.title || item.metadata.name}
      </div>
    ),
  },
  { id: 'type', name: 'Type', template: (item) => <Label theme={COMPONENT_TYPE_THEME[item.spec.type]}>{item.spec.type}</Label> },
  { id: 'lifecycle', name: 'Lifecycle', template: (item) => <Label theme={LIFECYCLE_THEME[item.spec.lifecycle]}>{item.spec.lifecycle}</Label> },
  { id: 'owner', name: 'Owner', template: ownerCell },
  { id: 'system', name: 'System', template: (item) => refName(item.spec.system) },
  { id: 'tags', name: 'Tags', template: (item) => <TagLabels tags={item.metadata.tags} tagColors={item.metadata.tagColors} /> },
]

export function ComponentsListPage() {
  const navigate = useNavigate()

  return (
    <EntityListPage
      title="Components"
      description="All components across every system"
      addLabel="Add Component"
      onAdd={() => navigate('/components/new')}
      fetchList={componentsApi.list}
      columns={columns}
      rowTo={(item) => `/components/${item.id}`}
      railFields={componentRailFields}
      remove={componentsApi.remove}
      extraFilters={(setFilter, values) => [
        {
          label: 'Type',
          value: values.type ?? null,
          onChange: (value) => setFilter('type', value),
          options: TYPE_OPTIONS,
        },
        {
          label: 'Lifecycle',
          value: values.lifecycle ?? null,
          onChange: (value) => setFilter('lifecycle', value),
          options: LIFECYCLE_OPTIONS,
        },
      ]}
    />
  )
}
