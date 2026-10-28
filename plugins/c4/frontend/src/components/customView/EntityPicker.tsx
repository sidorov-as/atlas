import { useEffect, useRef, useState } from 'react'
import { Xmark } from '@gravity-ui/icons'
import { Button, Icon, Loader, Text, TextInput, Tooltip } from '@gravity-ui/uikit'
import { useDebouncedValue } from 'frontend/lib/useDebouncedValue'
import { searchPickerEntities, type PickerEntity } from '../../lib/customViewApi'
import { entityIcon, entityMeta } from './entityIcons'

export interface EntityPickerProps {
  entities: PickerEntity[]
  /** Kinds the search covers: the level's kinds narrowed by the enabled entity types. */
  kinds: string[]
  /** Heading, e.g. "Entities" or "Root entities". */
  label: string
  onAdd: (entity: PickerEntity) => void
  onRemove: (id: string) => void
  /** Ids from a link that no longer exist; each is listed with a way to remove it. */
  missingIds?: string[]
  disabled?: boolean
}

function ResultRow({ entity, onSelect }: { entity: PickerEntity; onSelect: () => void }) {
  return (
    <button
      type="button"
      onClick={onSelect}
      style={{ display: 'flex', alignItems: 'center', gap: 8, width: '100%', padding: '6px 10px', border: 0, background: 'transparent', color: 'inherit', textAlign: 'left', cursor: 'pointer' }}
    >
      <Icon data={entityIcon(entity)} size={16} />
      <span style={{ minWidth: 0, flex: 1 }}>
        <Text ellipsis style={{ display: 'block' }}>{entity.name}</Text>
        <Text color="secondary" variant="caption-2">{entityMeta(entity)}</Text>
      </span>
    </button>
  )
}

/** Searchable multi-select over catalog entities, listing the chosen ones as compact removable rows. */
export function EntityPicker({ entities, kinds, label, onAdd, onRemove, missingIds = [], disabled }: EntityPickerProps) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [results, setResults] = useState<PickerEntity[]>([])
  const [loading, setLoading] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const debounced = useDebouncedValue(query, 250)
  const chosenKey = entities.map((entity) => entity.id).join(',')
  const kindsKey = kinds.join(',')

  useEffect(() => {
    if (!open || kinds.length === 0) { setResults([]); return }
    let cancelled = false
    setLoading(true)
    searchPickerEntities(debounced, kinds, entities.map((entity) => entity.id))
      .then((found) => { if (!cancelled) setResults(found) })
      .catch(() => { if (!cancelled) setResults([]) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, debounced, kindsKey, chosenKey])

  return (
    <div
      ref={containerRef}
      onBlur={(event) => { if (!containerRef.current?.contains(event.relatedTarget as Node | null)) setOpen(false) }}
      style={{ display: 'flex', flexDirection: 'column', gap: 8 }}
    >
      <Text variant="subheader-1">{label} ({entities.length + missingIds.length})</Text>
      <div style={{ position: 'relative' }}>
        <TextInput
          value={query}
          placeholder="Search by name"
          controlProps={{ 'aria-label': `Search ${label.toLowerCase()}` }}
          disabled={disabled}
          hasClear
          onUpdate={(value) => { setQuery(value); setOpen(true) }}
          onFocus={() => setOpen(true)}
          onKeyDown={(event) => { if (event.key === 'Escape') setOpen(false) }}
        />
        {open && (
          <div
            role="listbox"
            aria-label={`${label} search results`}
            style={{ position: 'absolute', zIndex: 10, left: 0, right: 0, top: '100%', marginTop: 4, maxHeight: 280, overflowY: 'auto', background: 'var(--g-color-base-float)', border: '1px solid var(--g-color-line-generic)', borderRadius: 8, boxShadow: '0 4px 16px var(--g-color-sfx-shadow)' }}
          >
            {loading && <div style={{ padding: 10 }}><Loader size="s" /></div>}
            {!loading && results.length === 0 && <Text color="secondary" style={{ display: 'block', padding: 10 }}>No matching entities</Text>}
            {!loading && results.map((entity) => (
              <ResultRow key={entity.id} entity={entity} onSelect={() => { onAdd(entity); setQuery(''); setOpen(false) }} />
            ))}
          </div>
        )}
      </div>
      {entities.length === 0 && missingIds.length === 0 && <Text color="secondary">Select at least one entity to build a view.</Text>}
      <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 4 }}>
        {entities.map((entity) => (
          <li key={entity.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '2px 4px 2px 8px', border: '1px solid var(--g-color-line-generic)', borderRadius: 6 }}>
            <Icon data={entityIcon(entity)} size={16} />
            <span style={{ minWidth: 0, flex: 1 }}>
              <Text ellipsis style={{ display: 'block' }}>{entity.name}</Text>
              <Text color="secondary" variant="caption-2">{entityMeta(entity)}</Text>
            </span>
            <Tooltip content={`Remove ${entity.name}`} placement="top">
              <Button view="flat" size="s" aria-label={`Remove ${entity.name}`} onClick={() => onRemove(entity.id)}><Icon data={Xmark} size={14} /></Button>
            </Tooltip>
          </li>
        ))}
        {missingIds.map((id) => (
          <li key={id} role="alert" style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '2px 4px 2px 8px', border: '1px solid var(--g-color-line-danger)', borderRadius: 6 }}>
            <span style={{ minWidth: 0, flex: 1 }}>
              <Text color="danger" style={{ display: 'block' }}>Entity not found</Text>
              <Text color="secondary" variant="caption-2" ellipsis>{id}</Text>
            </span>
            <Tooltip content={`Remove unknown entity ${id}`} placement="top">
              <Button view="flat" size="s" aria-label={`Remove unknown entity ${id}`} onClick={() => onRemove(id)}><Icon data={Xmark} size={14} /></Button>
            </Tooltip>
          </li>
        ))}
      </ul>
    </div>
  )
}
