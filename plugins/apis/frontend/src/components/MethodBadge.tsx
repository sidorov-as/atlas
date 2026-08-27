import { Label } from '@gravity-ui/uikit'
import { METHOD_THEME } from '../lib/badges'
import type { EndpointMethod } from '../lib/types'

/** Always renders the method text alongside its theme color (spec's "not distinguished by color alone" requirement). */
export function MethodBadge({ method }: { method: EndpointMethod }) {
  return <Label theme={METHOD_THEME[method]}>{method}</Label>
}
