// Shared row-actions menu builder for entity list tables.
import { Pencil, TrashBin } from '@gravity-ui/icons'
import { Icon, type TableAction } from '@gravity-ui/uikit'

/** Two-item Edit/Remove row-actions menu, identical across every entity list table. */
export function entityRowActions<T>(onEdit: () => void, onRemove: () => void): TableAction<T>[] {
  return [
    { text: 'Edit', icon: <Icon data={Pencil} size={16} />, theme: 'normal', handler: onEdit },
    { text: 'Remove', icon: <Icon data={TrashBin} size={16} />, theme: 'danger', handler: onRemove },
  ]
}
