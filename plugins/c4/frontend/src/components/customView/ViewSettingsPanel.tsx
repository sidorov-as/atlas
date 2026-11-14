import { useState } from 'react'
import { Button, Checkbox, Select, SegmentedRadioGroup, Text, TextInput } from '@gravity-ui/uikit'
import { entityTypesForLevel, type CustomViewDirection, type CustomViewEntityType, type CustomViewRelationships, type CustomViewSelection } from '../../lib/customView'
import { pickerKinds, type ActorKind, type PickerEntity } from '../../lib/customViewApi'
import { changeLevel, changeSelection, isDraftValid, isTypeLocked, type CustomViewDraft } from '../../lib/customViewDraft'
import { EntityPicker } from './EntityPicker'

export const PANEL_WIDTH = 360

const TYPE_LABELS: Record<CustomViewEntityType, string> = { component: 'Components', resource: 'Resources', api: 'APIs', actor: 'Actors' }
const TYPE_LOCKED_HINT = 'Remove selected entities of this type first'

function Field({ id, label, children }: { id: string; label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <Text as="label" htmlFor={id} color="secondary">{label}</Text>
      {children}
    </div>
  )
}

export interface ViewSettingsPanelProps {
  draft: CustomViewDraft
  onChange: (draft: CustomViewDraft) => void
  actorKinds: ActorKind[]
  /** Ids from the link that no longer exist. */
  missingIds: string[]
  onRemoveMissing: (id: string) => void
  loading: boolean
  onApply: () => void
  onReset: () => void
}

export function ViewSettingsPanel({ draft, onChange, actorKinds, missingIds, onRemoveMissing, loading, onApply, onReset }: ViewSettingsPanelProps) {
  const [levelNotice, setLevelNotice] = useState(false)
  const [lockedType, setLockedType] = useState<CustomViewEntityType | null>(null)
  const actorKindIds = actorKinds.map((entry) => entry.kind)
  const valid = isDraftValid(draft) && missingIds.length === 0
  const neighborhood = draft.selection === 'neighborhood'

  function update(next: Partial<CustomViewDraft>) {
    setLockedType(null)
    onChange({ ...draft, ...next })
  }

  function toggleType(type: CustomViewEntityType, checked: boolean) {
    if (!checked && isTypeLocked(draft, type, actorKindIds)) { setLockedType(type); return }
    update({ entityTypes: entityTypesForLevel(draft.level).filter((entry) => (entry === type ? checked : draft.entityTypes.includes(entry))) })
  }

  function addEntity(entity: PickerEntity) {
    if (!draft.entities.some((entry) => entry.id === entity.id)) update({ entities: [...draft.entities, entity] })
  }

  return (
    <form
      aria-label="View settings"
      onSubmit={(event) => { event.preventDefault(); if (valid && !loading) onApply() }}
      style={{ display: 'flex', flexDirection: 'column', gap: 16 }}
    >
      <Text variant="subheader-3">View settings</Text>

      <Field id="level" label="Level">
        <SegmentedRadioGroup
          name="custom-view-level"
          width="max"
          value={draft.level}
          onUpdate={(value) => {
            const result = changeLevel(draft, value as 'systems' | 'components', actorKindIds)
            setLockedType(null)
            setLevelNotice(result.cleared)
            onChange(result.draft)
          }}
          options={[{ value: 'systems', content: 'Systems' }, { value: 'components', content: 'Components' }]}
        />
      </Field>
      {levelNotice && <Text color="warning" role="status">Selection cleared for the new level</Text>}

      <Field id="selection" label="Selection">
        <Select
          id="selection"
          width="max"
          value={[draft.selection]}
          onUpdate={([value]) => { setLevelNotice(false); onChange(changeSelection(draft, value as CustomViewSelection, actorKindIds)) }}
          options={[{ value: 'selected', content: 'Selected entities only' }, { value: 'neighborhood', content: 'Neighborhood' }]}
          aria-label="Selection"
        />
      </Field>

      <EntityPicker
        label={neighborhood ? 'Root entities' : 'Entities'}
        entities={draft.entities}
        kinds={pickerKinds(draft.level, draft.entityTypes, actorKinds)}
        missingIds={missingIds}
        onAdd={addEntity}
        onRemove={(id) => {
          if (missingIds.includes(id)) onRemoveMissing(id)
          else update({ entities: draft.entities.filter((entity) => entity.id !== id) })
        }}
      />

      {neighborhood && (
        <>
          <Field id="depth" label="Depth">
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <TextInput
                type="number"
                size="m"
                value={draft.depth === 'all' ? '' : draft.depth === null ? '' : String(draft.depth)}
                disabled={draft.depth === 'all'}
                validationState={draft.depth === null ? 'invalid' : undefined}
                errorMessage="Enter a whole number of 1 or more"
                controlProps={{ min: 1, step: 1, 'aria-label': 'Depth' }}
                onUpdate={(value) => update({ depth: /^[1-9]\d*$/.test(value) ? Number(value) : null })}
              />
              <Checkbox
                checked={draft.depth === 'all'}
                onUpdate={(checked) => update({ depth: checked ? 'all' : 1 })}
                content="Unlimited"
              />
            </div>
          </Field>
          <Field id="direction" label="Direction">
            <SegmentedRadioGroup
              name="custom-view-direction"
              width="max"
              value={draft.direction}
              onUpdate={(value) => update({ direction: value as CustomViewDirection })}
              options={[{ value: 'both', content: 'Both' }, { value: 'outgoing', content: 'Outgoing' }, { value: 'incoming', content: 'Incoming' }]}
            />
          </Field>
        </>
      )}

      <div role="group" aria-label="Entity types" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <Text color="secondary">Entity types</Text>
        {entityTypesForLevel(draft.level).map((type) => (
          <Checkbox key={type} checked={draft.entityTypes.includes(type)} onUpdate={(checked) => toggleType(type, checked)} content={TYPE_LABELS[type]} />
        ))}
        {lockedType && <Text color="warning" role="status">{TYPE_LOCKED_HINT}</Text>}
      </div>

      <Field id="relationships" label="Relationships">
        <Select
          id="relationships"
          width="max"
          value={[draft.relationships]}
          onUpdate={([value]) => update({ relationships: value as CustomViewRelationships })}
          options={[{ value: 'declared', content: 'Declared only' }, { value: 'declared_and_derived', content: 'Declared plus derived' }]}
          aria-label="Relationships"
        />
      </Field>

      <div style={{ display: 'flex', gap: 8 }}>
        <Button view="action" type="submit" disabled={!valid || loading} loading={loading}>Apply view</Button>
        <Button view="outlined" onClick={onReset}>Reset</Button>
      </div>
    </form>
  )
}
