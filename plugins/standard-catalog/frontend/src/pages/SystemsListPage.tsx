import { useNavigate } from 'react-router-dom'
import { Button, Label, Link, Loader, Text, type TableColumnConfig } from '@gravity-ui/uikit'
import { EntityListPage, ownerCell } from 'frontend/components/EntityListPage'
import { TagLabels } from 'frontend/components/TagLabels'
import { systemsApi } from 'frontend/lib/entities'
import { systemRailFields } from 'frontend/lib/railFields'
import type { SystemEntity } from 'frontend/lib/types'
import { useAsync } from 'frontend/lib/useAsync'

export function SystemDocumentationPreview({ system }: { system: SystemEntity }) {
  const navigate = useNavigate()
  const { data, isLoading } = useAsync(() => systemsApi.docs(system.id, { pageSize: 5 }), [system.id])
  if (isLoading) return <Loader size="s" />
  if (!data || data.count === 0) return null
  return (
    <section style={{ marginTop: 20 }}>
      <Text variant="subheader-2" style={{ display: 'block', marginBottom: 8 }}>Documentation</Text>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {data.page.objectList.map((link) => (
          <div key={link.url} style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
            <div style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              <Link href={link.url} target="_blank" rel="noreferrer">{link.title || link.url}</Link>
            </div>
            {link.type && <div style={{ flexShrink: 0 }}><Label size="xs">{link.type}</Label></div>}
          </div>
        ))}
      </div>
      {data.count > 5 && <Button view="flat" onClick={() => navigate(`/systems/${system.id}?tab=docs`)}>More ({data.count})</Button>}
    </section>
  )
}

const columns: TableColumnConfig<SystemEntity>[] = [
  { id: 'name', name: 'Name', template: (item) => item.metadata.title || item.metadata.name },
  { id: 'description', name: 'Description', template: (item) => item.metadata.description || '—' },
  { id: 'owner', name: 'Owner', template: ownerCell },
  { id: 'tags', name: 'Tags', template: (item) => <TagLabels tags={item.metadata.tags} tagColors={item.metadata.tagColors} /> },
]

export function SystemsListPage() {
  const navigate = useNavigate()

  return (
    <EntityListPage
      title="Systems"
      description="All systems in the catalog"
      addLabel="Add System"
      onAdd={() => navigate('/systems/new')}
      fetchList={systemsApi.list}
      columns={columns}
      rowTo={(item) => `/systems/${item.id}`}
      railFields={systemRailFields}
      remove={systemsApi.remove}
      renderPreviewSection={(system) => <SystemDocumentationPreview system={system} />}
    />
  )
}
