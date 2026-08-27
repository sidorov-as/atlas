import { Button, Select, TextInput } from '@gravity-ui/uikit'
import type { ReactNode } from 'react'

export interface SelectFilterConfig {
  label: string
  value: string | null
  onChange: (value: string | null) => void
  options: { value: string; content: string }[]
}

export interface MultiSelectFilterConfig {
  label: string
  value: string[]
  onChange: (value: string[]) => void
  options: { value: string; content: string }[]
}

export type FilterConfig = SelectFilterConfig | MultiSelectFilterConfig

interface FilterBarProps {
  search: string
  onSearchChange: (value: string) => void
  filters?: FilterConfig[]
  /** Omitted (rather than disabled) for a read-only session — catalog-web-ui spec's "Read-only session sees no Add action". */
  addLabel?: string
  onAdd?: () => void
  extra?: ReactNode
}

/** Search + filter dropdowns + "Add X" action, shared by every entity list page (catalog-web-ui spec). */
export function FilterBar({ search, onSearchChange, filters = [], addLabel, onAdd, extra }: FilterBarProps) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap', marginBottom: 16 }}>
      <TextInput
        placeholder="Search…"
        value={search}
        onUpdate={onSearchChange}
        size="m"
        style={{ minWidth: 200, maxWidth: 320, flex: '1 1 240px' }}
        hasClear
      />
      {filters.map((filter) => (
        <Select
          key={filter.label}
          placeholder={filter.label}
          value={filter.value ? (Array.isArray(filter.value) ? filter.value : [filter.value]) : []}
          onUpdate={(value) => {
            if (Array.isArray(filter.value)) (filter.onChange as (values: string[]) => void)(value)
            else (filter.onChange as (nextValue: string | null) => void)(value[0] ?? null)
          }}
          options={filter.options}
          multiple={Array.isArray(filter.value)}
          hasClear
          width={160}
        />
      ))}
      {extra}
      {onAdd && (
        <Button view="action" onClick={onAdd} style={{ marginLeft: 'auto' }}>
          {addLabel}
        </Button>
      )}
    </div>
  )
}
