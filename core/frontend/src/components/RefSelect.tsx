import { Label, Select } from '@gravity-ui/uikit'
import { apisApi, componentsApi, groupsApi, resourcesApi, systemsApi, usersApi } from '../lib/entities'
import type { Paginated } from '../lib/types'
import { useAsync } from '../lib/useAsync'

interface NamedEntity {
  metadata: { name: string; title: string }
}

const LISTERS: Record<RefKind, () => Promise<NamedEntity[] | Paginated<NamedEntity>>> = {
  group: () => groupsApi.list({ pageSize: 100 }),
  system: () => systemsApi.list({ pageSize: 100 }),
  api: () => apisApi.list({ pageSize: 100 }),
  resource: () => resourcesApi.list({ pageSize: 100 }),
  component: () => componentsApi.list({ pageSize: 100 }),
  user: () => usersApi.list(),
}

export type RefKind = 'group' | 'system' | 'api' | 'resource' | 'component' | 'user'

function useRefItems(kind: RefKind): NamedEntity[] {
  const { data } = useAsync(LISTERS[kind], [kind])
  return Array.isArray(data) ? data : (data?.page.objectList ?? [])
}

function useRefOptions(kind: RefKind) {
  const items = useRefItems(kind)
  return items.map((item) => ({
    value: `${kind}:${item.metadata.name}`,
    content: item.metadata.title || item.metadata.name,
  }))
}

/** Single-select over every entity of `kind`, valued as a `kind:name` ref string (entity-catalog spec). */
export function RefSelect({
  kind,
  value,
  onChange,
  placeholder,
  allowEmpty,
}: {
  kind: RefKind
  value: string | null
  onChange: (value: string | null) => void
  placeholder: string
  allowEmpty?: boolean
}) {
  const options = useRefOptions(kind)
  return (
    <Select
      placeholder={placeholder}
      filterable
      filterPlaceholder="Search by name..."
      value={value ? [value] : []}
      onUpdate={(next) => onChange(next[0] ?? null)}
      options={options}
      hasClear={allowEmpty}
      width="max"
    />
  )
}

const TARGET_REF_KINDS: { kind: RefKind; label: string }[] = [
  { kind: 'system', label: 'System' },
  { kind: 'component', label: 'Component' },
  { kind: 'api', label: 'API' },
  { kind: 'resource', label: 'Resource' },
  { kind: 'user', label: 'User' },
  { kind: 'group', label: 'Group' },
]

/**
 * Searchable, typed catalog lookup for Architecture Relationship targets. Restricted to the
 * relationship-supported kinds (System, Component, API, Resource, User, Group), grouped and
 * labeled by kind so the target's kind stays visible alongside its display name.
 */
export function TargetRefSelect({
  value,
  onChange,
  placeholder,
}: {
  value: string | null
  onChange: (value: string | null) => void
  placeholder: string
}) {
  // Hooks must run unconditionally in a fixed order, so each kind gets its own call.
  const systems = useRefItems('system')
  const components = useRefItems('component')
  const apis = useRefItems('api')
  const resources = useRefItems('resource')
  const users = useRefItems('user')
  const groups = useRefItems('group')
  const itemsByKind: Record<RefKind, NamedEntity[]> = {
    system: systems,
    component: components,
    api: apis,
    resource: resources,
    user: users,
    group: groups,
  }

  const groupedOptions = TARGET_REF_KINDS.map(({ kind, label }) => ({
    label,
    options: itemsByKind[kind].map((item) => {
      const name = item.metadata.title || item.metadata.name
      return {
        value: `${kind}:${item.metadata.name}`,
        text: `${label} ${name}`,
        content: (
          <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <Label size="xs">{label}</Label>
            <span>{name}</span>
          </span>
        ),
      }
    }),
  })).filter((group) => group.options.length > 0)

  return (
    <Select
      placeholder={placeholder}
      filterable
      filterPlaceholder="Search by name..."
      value={value ? [value] : []}
      onUpdate={(next) => onChange(next[0] ?? null)}
      options={groupedOptions}
      hasClear
      width="max"
    />
  )
}

/** Multi-select over every entity of `kind`, valued as `kind:name` ref strings. */
export function MultiRefSelect({
  kind,
  value,
  onChange,
  placeholder,
}: {
  kind: RefKind
  value: string[]
  onChange: (value: string[]) => void
  placeholder: string
}) {
  const options = useRefOptions(kind)
  return (
    <Select
      placeholder={placeholder}
      multiple
      value={value}
      onUpdate={onChange}
      options={options}
      hasClear
      width="max"
    />
  )
}
