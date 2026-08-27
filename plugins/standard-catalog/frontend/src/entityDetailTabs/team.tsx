import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Label, Pagination, Select, Text } from '@gravity-ui/uikit'
import { entityDetailTab } from '@atlas/plugin-api'
import { EntityTable } from 'frontend/components/EntityTable'
import { MarkdownDescription } from 'frontend/components/MarkdownDescription'
import { TagLabels } from 'frontend/components/TagLabels'
import { apisApi, componentsApi, resourcesApi, systemsApi, tagsApi, type ListFilters } from 'frontend/lib/entities'
import type { CatalogEntityUnion, GroupEntity, Metadata, Paginated } from 'frontend/lib/types'
import { useAsync } from 'frontend/lib/useAsync'
import { useEntityRowActivation } from 'frontend/lib/useEntityRowActivation'

function isTeam(entity: CatalogEntityUnion): entity is GroupEntity {
  return entity.kind === 'Group'
}

function OwnedTable<T extends { id: string; metadata: Metadata }>({
  owner,
  fetchList,
  rowTo,
}: {
  owner: string
  fetchList: (filters: ListFilters) => Promise<Paginated<T>>
  rowTo: (item: T) => string
}) {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(15)
  const [tags, setTags] = useState<string[]>([])
  const { data: availableTags } = useAsync(() => tagsApi.list(), [])
  const { data } = useAsync(
    () => fetchList({ owner, tags: tags.length ? tags : undefined, page, pageSize }),
    [owner, tags.join(','), page, pageSize],
  )
  const { handleRowClick } = useEntityRowActivation<T>(
    (item) => String(item.id),
    (item) => navigate(rowTo(item)),
  )

  return (
    <>
      <div style={{ marginBottom: 8 }}>
        <Select
          placeholder="Tags"
          value={tags}
          onUpdate={(value) => { setTags(value); setPage(1) }}
          options={(availableTags ?? []).map((tag) => ({ value: tag.name, content: tag.name }))}
          multiple
          hasClear
          width={160}
        />
      </div>
      <EntityTable
        data={data?.page.objectList ?? []}
        getRowId={(item) => String(item.id)}
        onRowClick={handleRowClick}
        emptyMessage="None"
        columns={[
          { id: 'name', name: 'Name', template: (item) => item.metadata.title || item.metadata.name },
          { id: 'tags', name: 'Tags', template: (item) => <TagLabels tags={item.metadata.tags} tagColors={item.metadata.tagColors} /> },
        ]}
      />
      {data && data.count > pageSize && (
        <div style={{ marginTop: 16 }}>
          <Pagination
            page={page}
            pageSize={pageSize}
            total={data.count}
            pageSizeOptions={[15, 30, 50, 100]}
            showInput
            onUpdate={(nextPage, nextPageSize) => { setPage(nextPageSize === pageSize ? nextPage : 1); setPageSize(nextPageSize) }}
          />
        </div>
      )}
    </>
  )
}

function TeamOverviewTab({ entity }: { entity: CatalogEntityUnion }) {
  if (!isTeam(entity)) return null
  return <MarkdownDescription text={entity.metadata.description} />
}

function TeamMembersTab({ entity }: { entity: CatalogEntityUnion }) {
  if (!isTeam(entity)) return null
  const memberships = entity.spec.membershipGrants ?? entity.spec.members.map((member) => ({
    entity: member,
    effective: true,
    grants: [],
  }))
  if (memberships.length === 0) return <Text color="secondary">No members</Text>
  return (
    <div style={{ display: 'flex', gap: 12, flexDirection: 'column' }}>
      {memberships.map((membership) => (
        <div key={membership.entity} style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
          <Label theme={membership.effective ? 'success' : 'unknown'}>
            {membership.entity.replace(/^user:/, '')}
          </Label>
          {membership.grants.map((grant) => (
            <Label
              key={grant.id}
              size="xxs"
              theme={grant.applicable ? (grant.sourceKind === 'manual' ? 'normal' : 'info') : 'warning'}
              value={grant.legacyUnclassified ? 'legacy, unclassified' : (grant.applicable ? 'active' : 'inactive')}
            >
              {grant.sourceKind === 'manual' ? 'manual' : (grant.providerId ?? 'provider')}
            </Label>
          ))}
        </div>
      ))}
    </div>
  )
}

function TeamSystemsTab({ entity }: { entity: CatalogEntityUnion }) {
  if (!isTeam(entity)) return null
  return <OwnedTable owner={`group:${entity.metadata.name}`} fetchList={systemsApi.list} rowTo={(item) => `/systems/${item.id}`} />
}

function TeamComponentsTab({ entity }: { entity: CatalogEntityUnion }) {
  if (!isTeam(entity)) return null
  return <OwnedTable owner={`group:${entity.metadata.name}`} fetchList={componentsApi.list} rowTo={(item) => `/components/${item.id}`} />
}

function TeamResourcesTab({ entity }: { entity: CatalogEntityUnion }) {
  if (!isTeam(entity)) return null
  return <OwnedTable owner={`group:${entity.metadata.name}`} fetchList={resourcesApi.list} rowTo={(item) => `/resources/${item.id}`} />
}

function TeamApisTab({ entity }: { entity: CatalogEntityUnion }) {
  if (!isTeam(entity)) return null
  return <OwnedTable owner={`group:${entity.metadata.name}`} fetchList={apisApi.list} rowTo={(item) => `/apis/${item.id}`} />
}

export const teamEntityDetailTabs = [
  entityDetailTab<CatalogEntityUnion>({ id: 'atlas.standard-catalog.team.overview', value: 'overview', label: 'Overview', when: isTeam, component: TeamOverviewTab }),
  entityDetailTab<CatalogEntityUnion>({ id: 'atlas.standard-catalog.team.members', value: 'members', label: 'Members', when: isTeam, component: TeamMembersTab }),
  entityDetailTab<CatalogEntityUnion>({ id: 'atlas.standard-catalog.team.systems', value: 'systems', label: 'Systems', when: isTeam, component: TeamSystemsTab }),
  entityDetailTab<CatalogEntityUnion>({ id: 'atlas.standard-catalog.team.components', value: 'components', label: 'Components', when: isTeam, component: TeamComponentsTab }),
  entityDetailTab<CatalogEntityUnion>({ id: 'atlas.standard-catalog.team.resources', value: 'resources', label: 'Resources', when: isTeam, component: TeamResourcesTab }),
  entityDetailTab<CatalogEntityUnion>({ id: 'atlas.standard-catalog.team.apis', value: 'apis', label: 'APIs', when: isTeam, component: TeamApisTab }),
]
