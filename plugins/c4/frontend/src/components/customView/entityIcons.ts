import { Hierarchy, Person, Persons } from '@gravity-ui/icons'
import type { IconData } from '@gravity-ui/uikit'
import { apiTypeIcon, componentTypeIcon, resourceTypeIcon } from 'frontend/lib/icons'
import type { PickerEntity } from '../../lib/customViewApi'

export function entityIcon(entity: PickerEntity): IconData {
  switch (entity.kind) {
    case 'system': return Hierarchy
    case 'component': return componentTypeIcon(entity.type ?? '')
    case 'resource': return resourceTypeIcon(entity.type ?? '')
    case 'api': return apiTypeIcon(entity.type ?? '')
    case 'group': return Persons
    default: return Person
  }
}

const KIND_LABELS: Record<string, string> = {
  system: 'System', component: 'Component', resource: 'Resource', api: 'API', group: 'Group', user: 'User',
}

export function kindLabel(kind: string): string {
  return KIND_LABELS[kind] ?? kind.charAt(0).toUpperCase() + kind.slice(1)
}

export function entityMeta(entity: PickerEntity): string {
  return entity.system ? `${kindLabel(entity.kind)} · ${entity.system}` : kindLabel(entity.kind)
}
