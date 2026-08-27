// Spec affordances shared between ApiDetailPage's Overview and Documentation
// tabs: download (universal, every type/source) and the stale-fetch indicator
// (a universal download action and a stale-fetch indicator that reuses
// existing UI primitives) — split out of `frontend/components/ApiSpecPanel`
import { lazy, Suspense } from 'react'
import { Button, Icon, Label, Loader, Tooltip } from '@gravity-ui/uikit'
import { ArrowDownToLine } from '@gravity-ui/icons'
import type { ApiEntity } from 'frontend/lib/types'

// The renderer stack (redoc, @asyncapi/react-component, mobx, styled-components) is
// large and only ever needed on the Documentation tab, so it's its own chunk.
const ApiSpecDocViewer = lazy(() => import('./ApiSpecDocViewer'))

function specFileName(api: ApiEntity): string {
  const isJson = /^\s*[[{]/.test(api.spec.specContent)
  return `${api.metadata.name}-spec.${isJson ? 'json' : 'yaml'}`
}

export function downloadSpec(api: ApiEntity) {
  const blob = new Blob([api.spec.specContent], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = specFileName(api)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

/** Universal, shown whenever `specContent` is non-empty regardless of type/source. */
export function DownloadSpecButton({ api }: { api: ApiEntity }) {
  if (!api.spec.specContent) return null
  return (
    <Button view="outlined" onClick={() => downloadSpec(api)}>
      <Icon data={ArrowDownToLine} />
      Download spec
    </Button>
  )
}

/** Shown when `spec_resolve_failed` is true: last-good `spec_content` is stale. */
export function StaleSpecLabel() {
  return (
    <Tooltip content="The last refresh of the spec URL failed. This is the last successfully fetched copy." placement="top">
      <Label theme="danger">Stale spec</Label>
    </Tooltip>
  )
}

/** Shown when `endpoints_sync_failed` is true: the resolved spec couldn't be parsed into endpoints, so the endpoint list may be stale or incomplete (mirrors `StaleSpecLabel`). */
export function EndpointSyncFailedLabel() {
  return (
    <Tooltip content="The last attempt to import endpoints from this API's spec failed. The endpoint list may be out of date." placement="top">
      <Label theme="danger">Endpoint sync failed</Label>
    </Tooltip>
  )
}

/** Shown when `operations_sync_failed` is true: the resolved spec couldn't be parsed into operations, so the operation list may be stale or incomplete (mirrors `EndpointSyncFailedLabel`). */
export function OperationSyncFailedLabel() {
  return (
    <Tooltip content="The last attempt to import operations from this API's spec failed. The operation list may be out of date." placement="top">
      <Label theme="danger">Operation sync failed</Label>
    </Tooltip>
  )
}

/** Documentation tab body: renders `spec_content` via a type-specific viewer, falling back to download on failure. */
export function ApiDocumentationView({ api }: { api: ApiEntity }) {
  return (
    <Suspense fallback={<Loader size="m" />}>
      <ApiSpecDocViewer api={api} />
    </Suspense>
  )
}
