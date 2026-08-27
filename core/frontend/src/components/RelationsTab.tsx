import { useState } from 'react'
import { Alert, Button, Icon, Label, Loader, Select, Text, TextInput, Tooltip } from '@gravity-ui/uikit'
import { TriangleExclamation } from '@gravity-ui/icons'
import { ConfirmDialog } from './ConfirmDialog'
import { EntityTable } from './EntityTable'
import { RelationTargetLink } from './RelationTargetLink'
import { TargetRefSelect } from './RefSelect'
import { architectureRelationshipsApi } from '../lib/entities'
import { useSession } from '../lib/SessionContext'
import type { ArchitectureRelationship, Relation } from '../lib/types'
import { useAsync } from '../lib/useAsync'
import { useConfirm } from '../lib/useConfirm'

/**
 * Removed/deprecated warning badge for a relation's endpoint (surfaces a
 * removed or deprecated target's status) — `null` when neither applies.
 * `removed` takes precedence in the tooltip copy since it's the stronger signal;
 * both render together when both are true.
 */
export function LifecycleWarning({ status, deprecated }: { status: 'active' | 'removed', deprecated: boolean }) {
  if (status !== 'removed' && !deprecated) return null
  const messages = [
    status === 'removed' && 'This entity has been removed from the catalog.',
    deprecated && 'This entity is deprecated.',
  ].filter((message): message is string => Boolean(message))
  const tooltip = messages.join(' ')
  return (
    <Tooltip content={tooltip} placement="top">
      <span aria-label={tooltip} style={{ display: 'inline-flex', marginLeft: 4, verticalAlign: 'middle' }}>
        <Icon data={TriangleExclamation} size={14} style={{ color: 'var(--g-color-text-warning)' }} />
      </span>
    </Tooltip>
  )
}

const INTERACTION_KINDS = [
  { value: 'synchronous', content: 'Synchronous' },
  { value: 'asynchronous', content: 'Asynchronous' },
  { value: 'data-access', content: 'Data access' },
  { value: 'manual', content: 'Manual' },
] as const

interface RelationshipDraft {
  target: string
  label: string
  technology: string
  interactionKind: ArchitectureRelationship['interactionKind']
  tags: string
}

const EMPTY_DRAFT: RelationshipDraft = { target: '', label: '', technology: '', interactionKind: 'manual', tags: '' }

function relationshipDraft(relationship: ArchitectureRelationship): RelationshipDraft {
  return {
    target: relationship.target,
    label: relationship.label,
    technology: relationship.technology,
    interactionKind: relationship.interactionKind,
    tags: relationship.tags.join(', '),
  }
}

function canMutateRelationship(
  relationship: ArchitectureRelationship,
  source: string,
  canManageArchitectureRelationships: boolean,
) {
  return (
    canManageArchitectureRelationships
    && relationship.origin === 'manual'
    && relationship.source === source
  )
}

/** Renders derived catalog structure and declared architecture interactions separately. */
export function RelationsTab({
  fetchRelations,
  fetchArchitectureRelationships,
  source,
  canManageArchitectureRelationships: callerAllowsManagement,
}: {
  fetchRelations: () => Promise<Relation[]>
  fetchArchitectureRelationships: () => Promise<ArchitectureRelationship[]>
  source: string
  canManageArchitectureRelationships: boolean
}) {
  // Administrative and custom mutation controls obey read-only —
  // applies on top of (not instead of) the caller's own YAML-managed-provenance gate.
  const { session } = useSession()
  const canManageArchitectureRelationships = callerAllowsManagement && !session?.isReadOnly
  const { data: relations, error: relationsError, isLoading: relationsLoading } = useAsync(fetchRelations, [])
  const {
    data: architectureRelationships,
    error: architectureRelationshipsError,
    isLoading: architectureRelationshipsLoading,
    reload: reloadArchitectureRelationships,
  } = useAsync(fetchArchitectureRelationships, [])
  const [draft, setDraft] = useState<RelationshipDraft | null>(null)
  const [editing, setEditing] = useState<ArchitectureRelationship | null>(null)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const { confirm, dialogProps } = useConfirm()

  async function saveRelationship() {
    if (!draft) return
    setSaveError(null)
    if (!draft.target.trim() || !draft.label.trim()) {
      setSaveError('Target and relationship label are required.')
      return
    }
    setIsSaving(true)
    try {
      const input = {
        source,
        target: draft.target.trim(),
        label: draft.label.trim(),
        technology: draft.technology.trim(),
        interactionKind: draft.interactionKind,
        tags: draft.tags.split(',').map((tag) => tag.trim()).filter(Boolean),
      }
      if (editing) await architectureRelationshipsApi.update(editing.id, input)
      else await architectureRelationshipsApi.create(input)
      setDraft(null)
      setEditing(null)
      await reloadArchitectureRelationships()
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : 'Unable to save the architecture relationship.')
    } finally {
      setIsSaving(false)
    }
  }

  async function deleteRelationship(relationship: ArchitectureRelationship) {
    if (!(await confirm({ title: 'Delete relationship', message: `Delete the relationship "${relationship.label}"? This cannot be undone.`, preset: 'danger' }))) return
    setSaveError(null)
    try {
      await architectureRelationshipsApi.remove(relationship.id)
      await reloadArchitectureRelationships()
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : 'Unable to delete the architecture relationship.')
    }
  }

  if (relationsLoading && architectureRelationshipsLoading && !relations && !architectureRelationships) return <Loader size="m" />
  if (relationsError) return <Alert theme="danger" message={relationsError.message} />
  if (architectureRelationshipsError) return <Alert theme="danger" message={architectureRelationshipsError.message} />

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 32 }}>
      <section>
        <Text variant="subheader-2" style={{ display: 'block', marginBottom: 12 }}>Catalog Relations</Text>
        <EntityTable
          data={relations ?? []}
          columns={[
            { id: 'predicate', name: 'Relation' },
            {
              id: 'target',
              name: 'Target',
              template: (relation) => (
                <>
                  <RelationTargetLink target={relation.target} targetKind={relation.targetKind} targetId={relation.targetId} />
                  <LifecycleWarning status={relation.status} deprecated={relation.deprecated} />
                </>
              ),
            },
          ]}
          getRowId={(_item, index) => String(index)}
          emptyMessage="No catalog relations"
        />
      </section>

      <section>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginBottom: 12 }}>
          <Text variant="subheader-2">Architecture Relationships</Text>
          {canManageArchitectureRelationships && !draft && (
            <Button size="s" view="action" onClick={() => { setEditing(null); setDraft(EMPTY_DRAFT); setSaveError(null) }}>
              Add relationship
            </Button>
          )}
        </div>
        {!canManageArchitectureRelationships && (
          <Text color="secondary" style={{ display: 'block', marginBottom: 12 }}>
            Architecture relationships declared in YAML are read-only.
          </Text>
        )}
        {draft && (
          <div style={{ border: '1px solid var(--g-color-line-generic)', borderRadius: 8, padding: 16, marginBottom: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
            <Text variant="subheader-2">{editing ? 'Edit architecture relationship' : 'Add architecture relationship'}</Text>
            {saveError && <Alert theme="danger" message={saveError} />}
            <div>
              <Text color="secondary">Target</Text>
              <TargetRefSelect
                value={draft.target || null}
                onChange={(target) => setDraft({ ...draft, target: target ?? '' })}
                placeholder="Search Systems, Components, APIs, Resources, Users, Groups"
              />
            </div>
            <div>
              <Text color="secondary">Relationship label</Text>
              <TextInput value={draft.label} onUpdate={(label) => setDraft({ ...draft, label })} placeholder="Makes API calls to" />
            </div>
            <div>
              <Text color="secondary">Technology</Text>
              <TextInput value={draft.technology} onUpdate={(technology) => setDraft({ ...draft, technology })} placeholder="REST/HTTPS" />
            </div>
            <div>
              <Text color="secondary">Interaction kind</Text>
              <Select value={[draft.interactionKind]} onUpdate={(value) => setDraft({ ...draft, interactionKind: value[0] as RelationshipDraft['interactionKind'] })} options={[...INTERACTION_KINDS]} width="max" />
            </div>
            <div>
              <Text color="secondary">Tags (comma-separated)</Text>
              <TextInput value={draft.tags} onUpdate={(tags) => setDraft({ ...draft, tags })} placeholder="critical, external" />
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <Button view="action" loading={isSaving} onClick={() => void saveRelationship()}>{editing ? 'Save' : 'Create'}</Button>
              <Button view="outlined" disabled={isSaving} onClick={() => { setDraft(null); setEditing(null); setSaveError(null) }}>Cancel</Button>
            </div>
          </div>
        )}
        {saveError && !draft && <div style={{ marginBottom: 12 }}><Alert theme="danger" message={saveError} /></div>}
        <EntityTable
          data={architectureRelationships ?? []}
          columns={[
            {
              id: 'source',
              name: 'Source',
              template: (relationship) => (
                <>
                  <RelationTargetLink
                    target={relationship.source}
                    targetKind={relationship.sourceKind}
                    targetId={relationship.sourceId}
                  />
                  <LifecycleWarning status={relationship.sourceStatus} deprecated={relationship.sourceDeprecated} />
                </>
              ),
            },
            { id: 'label', name: 'Relationship' },
            {
              id: 'target',
              name: 'Target',
              template: (relationship) => (
                <>
                  <RelationTargetLink target={relationship.target} targetKind={relationship.targetKind} targetId={relationship.targetId} />
                  <LifecycleWarning status={relationship.targetStatus} deprecated={relationship.targetDeprecated} />
                </>
              ),
            },
            { id: 'technology', name: 'Technology', template: (relationship) => relationship.technology || '—' },
            { id: 'interactionKind', name: 'Kind' },
            {
              id: 'tags',
              name: 'Tags',
              template: (relationship) => relationship.tags.length ? (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  {relationship.tags.map((tag) => <Label key={tag}>{tag}</Label>)}
                </div>
              ) : '—',
            },
            { id: 'origin', name: 'Origin' },
            {
              id: 'actions',
              name: '',
              template: (relationship) => canMutateRelationship(
                relationship,
                source,
                canManageArchitectureRelationships,
              ) ? (
                <div style={{ display: 'flex', gap: 4 }}>
                  <Button size="s" view="flat" onClick={() => { setEditing(relationship); setDraft(relationshipDraft(relationship)); setSaveError(null) }}>Edit</Button>
                  <Button size="s" view="flat-danger" onClick={() => void deleteRelationship(relationship)}>Delete</Button>
                </div>
              ) : <Text color="secondary">Read-only</Text>,
            },
          ]}
          getRowId={(relationship) => String(relationship.id)}
          emptyMessage="No architecture relationships"
        />
      </section>
      <ConfirmDialog {...dialogProps} />
    </div>
  )
}
