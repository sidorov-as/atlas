import type { CustomViewFetchError } from './customViewApi'

/** An actionable message for a failed diagram request; `hasPrevious` says an earlier diagram is still on screen. */
export function failureMessage(error: CustomViewFetchError, hasPrevious: boolean): string {
  const prefix = hasPrevious ? 'The new settings were not applied; the previous diagram is still shown. ' : 'The view could not be built. '
  if (error.code === 'node_limit_exceeded') {
    return `${prefix}The view has ${error.count} nodes but the limit is ${error.limit}. Reduce the depth or the selection.`
  }
  if (error.code === 'unknown_entity') return `${prefix}An entity in this view no longer exists.`
  if (error.status >= 500 || error.status === 0) return `${prefix}The diagram could not be rendered.`
  return `${prefix}${error.message}`
}

export function isRenderFailure(error: CustomViewFetchError): boolean {
  return error.status >= 500 || error.status === 0
}
