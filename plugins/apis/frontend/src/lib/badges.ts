// Endpoint-specific badge theming — mirrors the shape of `frontend/lib/badges`'
// per-kind theme maps, scoped to this plugin since HTTP methods/status codes
// are only meaningful for Endpoint UI.
import type { LabelProps } from '@gravity-ui/uikit'
import type { OperationDirection, OperationRole } from './types'

/** HTTP method -> badge theme. Text is always rendered alongside the color (spec's
 * "not distinguished by color alone" requirement) — this theme only supplies emphasis. */
export const METHOD_THEME: Record<string, LabelProps['theme']> = {
  GET: 'info',
  POST: 'success',
  PUT: 'warning',
  PATCH: 'utility',
  DELETE: 'danger',
  HEAD: 'normal',
  OPTIONS: 'clear',
}

/** Response status code -> badge theme, keyed by leading digit (2xx/3xx/4xx/5xx). */
export function statusCodeTheme(statusCode: string): LabelProps['theme'] {
  switch (statusCode.charAt(0)) {
    case '2':
      return 'success'
    case '3':
      return 'info'
    case '4':
      return 'warning'
    case '5':
      return 'danger'
    default:
      return 'normal'
  }
}

/** `Operation.direction` -> badge theme. Text is always "Send"/"Receive" alongside the color — never `Publish`/`Subscribe`. */
export const DIRECTION_THEME: Record<OperationDirection, LabelProps['theme']> = {
  send: 'success',
  receive: 'info',
}

/** `ServiceOperationUsage.role` -> badge theme — a deliberately different vocabulary from direction ("Publisher"/"Subscriber", never "Send"/"Receive"). */
export const ROLE_THEME: Record<OperationRole, LabelProps['theme']> = {
  publisher: 'success',
  subscriber: 'utility',
}
