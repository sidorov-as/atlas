import { Label } from '@gravity-ui/uikit'
import { ROLE_THEME } from '../lib/badges'
import type { OperationRole } from '../lib/types'

const ROLE_LABEL: Record<OperationRole, string> = { publisher: 'Publisher', subscriber: 'Subscriber' }

/** Deliberately different vocabulary from `DirectionBadge` — "Publisher"/"Subscriber", never "Send"/"Receive", so a human-asserted role is never visually confused with the operation's own spec-derived direction. */
export function RoleBadge({ role }: { role: OperationRole }) {
  return <Label theme={ROLE_THEME[role]}>{ROLE_LABEL[role]}</Label>
}
