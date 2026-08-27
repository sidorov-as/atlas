import { useState } from 'react'
import { Alert, Button, Loader, Text, type TableColumnConfig } from '@gravity-ui/uikit'
import { Check } from '@gravity-ui/icons'
import { EntityTable } from '../components/EntityTable'
import { TagLabels } from '../components/TagLabels'
import { tagsApi } from '../lib/entities'
import { tagColorKey, TAG_PALETTE, type Tag, type TagColorKey } from '../lib/types'
import { useAsync } from '../lib/useAsync'
import { useSession } from '../lib/SessionContext'

interface TagColorEditorProps {
  tag: Tag
  onSave: (color: string) => Promise<void>
}

/** Swatch picker over the fixed palette + save button for one tag row; local until explicitly saved. */
function TagColorEditor({ tag, onSave }: TagColorEditorProps) {
  const [color, setColor] = useState<TagColorKey>(tagColorKey(tag.color))
  const [isSaving, setIsSaving] = useState(false)
  const isDirty = color !== tag.color

  async function handleSave() {
    setIsSaving(true)
    try {
      await onSave(color)
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ display: 'flex', gap: 4 }}>
        {TAG_PALETTE.map((key) => (
          <button
            key={key}
            type="button"
            onClick={() => setColor(key)}
            aria-label={`Set color for tag ${tag.name} to ${key}`}
            aria-pressed={color === key}
            className={`tag-preset-${key}`}
            style={{
              width: 22,
              height: 22,
              borderRadius: '50%',
              border: color === key ? '2px solid var(--g-color-text-primary)' : '1px solid var(--g-color-line-generic)',
              background: 'var(--tag-bg)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              padding: 0,
            }}
          >
            {color === key && <Check width={12} height={12} style={{ color: 'var(--tag-fg)' }} />}
          </button>
        ))}
      </div>
      <Button size="s" view="outlined" disabled={!isDirty} loading={isSaving} onClick={() => void handleSave()}>
        Save
      </Button>
    </div>
  )
}

/** Lists every known tag with an inline color editor, backed by the admin-only tag color API (tag-management spec). */
export function SettingsTagsPage() {
  const { data, isLoading, error, reload } = useAsync(() => tagsApi.list(), [])
  const [saveError, setSaveError] = useState<string | null>(null)
  // catalog-web-ui spec's "Read-only administrator opens settings" — mutation-trigger controls
  // are absent for a read-only session even though `SettingsLayout` already requires isAdmin.
  const { session } = useSession()
  const isReadOnly = Boolean(session?.isReadOnly)

  async function handleSave(tag: Tag, color: string) {
    setSaveError(null)
    try {
      await tagsApi.updateColor(tag.id, color)
      reload()
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Failed to update tag color')
    }
  }

  const columns: TableColumnConfig<Tag>[] = [
    {
      id: 'color',
      name: 'Color',
      template: (tag) => (
        isReadOnly
          ? <TagLabels tags={[tag.name]} tagColors={{ [tag.name]: tag.color }} />
          : <TagColorEditor key={`${tag.id}-${tag.color}`} tag={tag} onSave={(color) => handleSave(tag, color)} />
      ),
    },
    { id: 'name', name: 'Tag', template: (tag) => tag.name },
  ]

  return (
    <div>
      <Text variant="subheader-2">Tag colors</Text>
      <p>
        <Text color="secondary">Configure the color used to render each tag across the catalog</Text>
      </p>
      {error && <Alert theme="danger" message={error.message} />}
      {saveError && <Alert theme="danger" message={saveError} />}
      {isLoading && !data ? (
        <Loader size="m" />
      ) : (
        <EntityTable
          data={data ?? []}
          columns={columns}
          getRowId={(tag) => String(tag.id)}
          emptyMessage="No tags yet — tags appear here once used on an entity"
        />
      )}
    </div>
  )
}
