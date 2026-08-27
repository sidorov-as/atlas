import { Label } from '@gravity-ui/uikit'
import { DIRECTION_THEME } from '../lib/badges'
import type { OperationDirection } from '../lib/types'

const DIRECTION_LABEL: Record<OperationDirection, string> = { send: 'Send', receive: 'Receive' }

/** Always renders "Send"/"Receive" text alongside its theme color (spec's "not distinguished by color alone" requirement) — never `Publish`/`Subscribe`. */
export function DirectionBadge({ direction }: { direction: OperationDirection }) {
  return <Label theme={DIRECTION_THEME[direction]}>{DIRECTION_LABEL[direction]}</Label>
}
