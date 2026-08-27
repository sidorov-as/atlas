import { useEffect, useId, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Alert, Button, Checkbox, Dialog, Icon, Label, Loader, Pagination, Select, Text, TextArea, TextInput } from '@gravity-ui/uikit'
import { ArrowUpRightFromSquare, Copy, CopyCheck } from '@gravity-ui/icons'
import { entityDetailTab } from '@atlas/plugin-api'
import { ConfirmDialog } from 'frontend/components/ConfirmDialog'
import { DocumentationPreview } from 'frontend/components/DocumentationPreview'
import { EntityActionsTable, EntityTable } from 'frontend/components/EntityTable'
import { HistoryTab } from 'frontend/components/HistoryTab'
import { RelationsTab } from 'frontend/components/RelationsTab'
import { TagLabels } from 'frontend/components/TagLabels'
import { errorMessage } from 'frontend/lib/api'
import { architectureRelationshipsApi, apisApi, componentsApi, resourcesApi, systemsApi, tagsApi, type ListFilters } from 'frontend/lib/entities'
import { entityRowActions } from 'frontend/lib/entityRowActions'
import { useSession } from 'frontend/lib/SessionContext'
import type { CatalogEntityUnion, EntityStatus, LinkOut, Metadata, Paginated, SystemEntity } from 'frontend/lib/types'
import { useAsync } from 'frontend/lib/useAsync'
import { useConfirm } from 'frontend/lib/useConfirm'
import { useEntityRowActivation } from 'frontend/lib/useEntityRowActivation'

function isSystem(entity: CatalogEntityUnion): entity is SystemEntity {
  return entity.kind === 'System'
}

/** entity-removal-lifecycle spec: a removed System's own `status` is never cascaded onto its
 * children's `status` (D10) — this banner is the visual signal that closes the gap, since
 * without it a removed System's still-`active` Components/Resources/APIs look untouched. */
function ParentRemovedBanner({ kind }: { kind: string }) {
  return (
    <Alert
      theme="warning"
      message={`This System is removed — the ${kind} below keep their own status, but their parent is gone.`}
      style={{ marginBottom: 16 }}
    />
  )
}

function ChildTable<T extends { id: string; metadata: Metadata; status?: EntityStatus }>({
  fetchList,
  system,
  rowTo,
  parentRemoved,
  childKindLabel,
}: {
  fetchList: (filters: ListFilters) => Promise<Paginated<T>>
  system: string
  rowTo: (item: T) => string
  parentRemoved: boolean
  childKindLabel: string
}) {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(15)
  const [tags, setTags] = useState<string[]>([])
  const [showRemoved, setShowRemoved] = useState(false)
  const { data: availableTags } = useAsync(() => tagsApi.list(), [])
  const { data } = useAsync(
    () => fetchList({
      system, tags: tags.length ? tags : undefined, status: showRemoved ? 'all' : undefined, page, pageSize,
    }),
    [system, tags.join(','), showRemoved, page, pageSize],
  )
  const { handleRowClick } = useEntityRowActivation<T>(
    (item) => String(item.id),
    (item) => navigate(rowTo(item)),
  )
  return (
    <>
      {parentRemoved && <ParentRemovedBanner kind={childKindLabel} />}
      <div style={{ marginBottom: 8, display: 'flex', alignItems: 'center', gap: 12 }}>
        <Select
          placeholder="Tags"
          value={tags}
          onUpdate={(value) => { setTags(value); setPage(1) }}
          options={(availableTags ?? []).map((tag) => ({ value: tag.name, content: tag.name }))}
          multiple
          hasClear
          width={160}
        />
        <Checkbox checked={showRemoved} onUpdate={(checked) => { setShowRemoved(checked); setPage(1) }}>
          Show removed
        </Checkbox>
      </div>
      <EntityTable
        data={data?.page.objectList ?? []}
        getRowId={(item) => String(item.id)}
        onRowClick={handleRowClick}
        emptyMessage="None"
        columns={[
          { id: 'name', name: 'Name', template: (item) => item.metadata.title || item.metadata.name },
          { id: 'description', name: 'Description', template: (item) => item.metadata.description || '—' },
          { id: 'tags', name: 'Tags', template: (item) => <TagLabels tags={item.metadata.tags} tagColors={item.metadata.tagColors} /> },
          ...(showRemoved
            ? [{
                id: 'status',
                name: 'Status',
                template: (item: T) => (item.status === 'removed' ? <Label theme="warning">Removed</Label> : null),
              }]
            : []),
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

function SystemOverviewTab({ entity }: { entity: CatalogEntityUnion }) {
  if (!isSystem(entity)) return null
  return <DocumentationPreview value={entity.metadata.documentation} />
}

function SystemComponentsTab({ entity }: { entity: CatalogEntityUnion }) {
  if (!isSystem(entity)) return null
  return (
    <ChildTable
      system={`system:${entity.metadata.name}`}
      fetchList={componentsApi.list}
      rowTo={(item) => `/components/${item.id}`}
      parentRemoved={entity.status === 'removed'}
      childKindLabel="Components"
    />
  )
}

function SystemResourcesTab({ entity }: { entity: CatalogEntityUnion }) {
  if (!isSystem(entity)) return null
  return (
    <ChildTable
      system={`system:${entity.metadata.name}`}
      fetchList={resourcesApi.list}
      rowTo={(item) => `/resources/${item.id}`}
      parentRemoved={entity.status === 'removed'}
      childKindLabel="Resources"
    />
  )
}

function SystemApisTab({ entity }: { entity: CatalogEntityUnion }) {
  if (!isSystem(entity)) return null
  return (
    <ChildTable
      system={`system:${entity.metadata.name}`}
      fetchList={apisApi.list}
      rowTo={(item) => `/apis/${item.id}`}
      parentRemoved={entity.status === 'removed'}
      childKindLabel="APIs"
    />
  )
}

function DocumentLinkDialog({
  link,
  existingUrls,
  onClose,
  onSave,
}: {
  link: LinkOut | null
  existingUrls: Set<string>
  onClose: () => void
  onSave: (link: LinkOut) => Promise<void>
}) {
  const titleId = useId()
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [url, setUrl] = useState('')
  const [type, setType] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  useEffect(() => {
    setTitle(link?.title ?? '')
    setDescription(link?.description ?? '')
    setUrl(link?.url ?? '')
    setType(link?.type ?? '')
    setSubmitError(null)
  }, [link])

  async function handleSave() {
    const normalizedTitle = title.trim()
    const normalizedUrl = url.trim()
    if (!normalizedTitle) {
      setSubmitError('Title is required')
      return
    }
    if (!normalizedUrl) {
      setSubmitError('URL is required')
      return
    }
    if (existingUrls.has(normalizedUrl)) {
      setSubmitError('A link with this URL already exists')
      return
    }
    setSubmitting(true)
    setSubmitError(null)
    try {
      await onSave({ url: normalizedUrl, title: normalizedTitle, description: description.trim(), type: type.trim() })
      onClose()
    } catch (err) {
      setSubmitError(errorMessage(err, 'Failed to save link'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={link !== undefined} onClose={onClose} aria-labelledby={titleId} size="m">
      <Dialog.Header caption={link ? 'Edit link' : 'Add link'} id={titleId} />
      <Dialog.Body>
        <div style={{ display: 'grid', gap: 12 }}>
          <div><Text color="secondary">Title *</Text><TextInput value={title} onUpdate={setTitle} placeholder="Title" aria-required /></div>
          <div><Text color="secondary">Description</Text><TextArea value={description} onUpdate={setDescription} placeholder="Description (optional)" minRows={2} /></div>
          <div><Text color="secondary">URL</Text><TextInput value={url} onUpdate={setUrl} placeholder="https://…" autoFocus /></div>
          <div><Text color="secondary">Type</Text><TextInput value={type} onUpdate={setType} placeholder="Type (optional)" /></div>
          {submitError && <Alert theme="danger" message={submitError} />}
        </div>
      </Dialog.Body>
      <Dialog.Footer
        textButtonApply={link ? 'Save' : 'Add'}
        textButtonCancel="Cancel"
        onClickButtonCancel={onClose}
        onClickButtonApply={() => void handleSave()}
        loading={submitting}
      />
    </Dialog>
  )
}

function SystemDocsTab({ entity }: { entity: CatalogEntityUnion }) {
  const { session } = useSession()
  const [searchParams, setSearchParams] = useSearchParams()
  const q = searchParams.get('q') ?? ''
  const page = Number(searchParams.get('page') ?? '1') || 1
  const [copyMessage, setCopyMessage] = useState<string | null>(null)
  const [copiedUrl, setCopiedUrl] = useState<string | null>(null)
  const [editingLink, setEditingLink] = useState<LinkOut | null | undefined>(undefined)
  const [links, setLinks] = useState(entity.metadata.links)
  const { confirm, dialogProps } = useConfirm()
  const { data, error, isLoading, reload } = useAsync(
    () => systemsApi.docs(entity.id, { q: q || undefined, page, pageSize: 20 }),
    [entity.id, q, page],
  )
  const updateParams = (nextQ: string, nextPage: number) => {
    const next = new URLSearchParams(searchParams)
    if (nextQ) next.set('q', nextQ); else next.delete('q')
    if (nextPage > 1) next.set('page', String(nextPage)); else next.delete('page')
    setSearchParams(next)
  }
  useEffect(() => setLinks(entity.metadata.links), [entity.metadata.links])

  async function copy(url: string) {
    try {
      await navigator.clipboard.writeText(url)
      setCopyMessage('Link copied')
      setCopiedUrl(url)
    } catch {
      setCopyMessage('Could not copy link')
    }
  }
  async function saveLinks(nextLinks: LinkOut[]) {
    await systemsApi.update(entity.id, { metadata: { links: nextLinks } })
    setLinks(nextLinks)
    reload()
  }
  async function saveLink(nextLink: LinkOut) {
    const nextLinks = editingLink
      ? links.map((link) => link.url === editingLink.url ? nextLink : link)
      : [...links, nextLink]
    await saveLinks(nextLinks)
  }
  async function deleteLink(link: LinkOut) {
    if (!(await confirm({
      title: 'Delete link',
      message: `Delete "${link.title}"? This action cannot be undone.`,
      confirmText: 'Delete',
      preset: 'danger',
    }))) return
    await saveLinks(links.filter((item) => item.url !== link.url))
  }
  if (!isSystem(entity)) return null
  const canManageDocumentLinks = !entity.ingestedFrom && !session?.isReadOnly
  const existingUrls = new Set(links.filter((link) => link.url !== editingLink?.url).map((link) => link.url))
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <TextInput value={q} onUpdate={(value) => updateParams(value, 1)} placeholder="Search documentation" />
        {canManageDocumentLinks && <Button view="action" onClick={() => setEditingLink(null)}>Add</Button>}
      </div>
      {copyMessage && <Alert theme={copyMessage === 'Link copied' ? 'success' : 'danger'} message={copyMessage} />}
      {isLoading && <Loader size="m" />}
      {error && <Alert theme="danger" message={error.message} />}
      {data && <>
        <EntityActionsTable
          data={data.page.objectList}
          getRowId={(link) => link.url}
          emptyMessage={q ? 'No matching docs' : 'No docs linked'}
          columns={[
            { id: 'title', name: 'Title', template: (link) => link.title || link.url },
            { id: 'type', name: 'Type', template: (link) => link.type ? <Label size="xs">{link.type}</Label> : '—' },
            { id: 'description', name: 'Description', template: (link) => link.description || '—' },
            {
              id: 'link', name: 'Link', template: (link) => <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <Button view="flat" size="s" aria-label={`Open ${link.title || link.url}`} href={link.url} target="_blank" rel="noreferrer"><Icon data={ArrowUpRightFromSquare} size={16} /></Button>
                <Button view="flat" size="s" aria-label={`Copy ${link.title || link.url}`} onClick={() => void copy(link.url)}><Icon data={copiedUrl === link.url ? CopyCheck : Copy} size={16} /></Button>
              </div>,
            },
          ]}
          getRowActions={canManageDocumentLinks ? (link) => entityRowActions(
            () => setEditingLink(link),
            () => void deleteLink(link),
          ) : undefined}
        />
        {data.numPages > 1 && <Pagination page={page} pageSize={20} total={data.count} onUpdate={(nextPage) => updateParams(q, nextPage)} />}
      </>}
      {canManageDocumentLinks && editingLink !== undefined && <DocumentLinkDialog link={editingLink} existingUrls={existingUrls} onClose={() => setEditingLink(undefined)} onSave={saveLink} />}
      <ConfirmDialog {...dialogProps} />
    </div>
  )
}

function SystemRelationsTab({ entity }: { entity: CatalogEntityUnion }) {
  if (!isSystem(entity)) return null
  const systemRef = `system:${entity.metadata.name}`
  return (
    <RelationsTab
      fetchRelations={() => systemsApi.relations(entity.id)}
      fetchArchitectureRelationships={() => architectureRelationshipsApi.list(systemRef)}
      source={systemRef}
      canManageArchitectureRelationships={!entity.ingestedFrom}
    />
  )
}

function SystemHistoryTab({ entity }: { entity: CatalogEntityUnion }) {
  if (!isSystem(entity)) return null
  return <HistoryTab fetchHistory={() => systemsApi.history(entity.id)} />
}

export const systemEntityDetailTabs = [
  entityDetailTab<CatalogEntityUnion>({ id: 'atlas.standard-catalog.system.overview', value: 'overview', label: 'Overview', when: isSystem, component: SystemOverviewTab }),
  entityDetailTab<CatalogEntityUnion>({ id: 'atlas.standard-catalog.system.components', value: 'components', label: 'Components', when: isSystem, component: SystemComponentsTab }),
  entityDetailTab<CatalogEntityUnion>({ id: 'atlas.standard-catalog.system.resources', value: 'resources', label: 'Resources', when: isSystem, component: SystemResourcesTab }),
  entityDetailTab<CatalogEntityUnion>({ id: 'atlas.standard-catalog.system.apis', value: 'apis', label: 'APIs', when: isSystem, component: SystemApisTab }),
  entityDetailTab<CatalogEntityUnion>({ id: 'atlas.standard-catalog.system.docs', value: 'docs', label: 'Docs', when: isSystem, component: SystemDocsTab }),
  entityDetailTab<CatalogEntityUnion>({ id: 'atlas.standard-catalog.system.relations', value: 'relations', label: 'Relations', when: isSystem, component: SystemRelationsTab }),
  entityDetailTab<CatalogEntityUnion>({ id: 'atlas.standard-catalog.system.history', value: 'history', label: 'History', when: isSystem, component: SystemHistoryTab }),
]
