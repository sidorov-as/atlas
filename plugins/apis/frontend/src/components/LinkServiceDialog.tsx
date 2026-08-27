// Link Service dialog — service search/select
// (already-linked services shown disabled with an "Already linked" marker),
// team display, and an informational note when linking will also create
// `consumesAPI`. Never rendered for a `removed`
// endpoint — the caller (EndpointLinkedServicesTab) doesn't offer the
// trigger at all in that state.
import { useEffect, useId, useState } from 'react'
import { Dialog, Label, Select, Text } from '@gravity-ui/uikit'
import { errorMessage } from 'frontend/lib/api'
import { componentsApi } from 'frontend/lib/entities'
import { refName, type ApiEntity } from 'frontend/lib/types'
import { useAsync } from 'frontend/lib/useAsync'
import { endpointServicesApi } from '../lib/entities'
import type { Endpoint, EndpointServiceLink } from '../lib/types'

export function LinkServiceDialog({
  open,
  onClose,
  endpoint,
  api,
  linkedServiceIds,
  onLinked,
}: {
  open: boolean
  onClose: () => void
  endpoint: Endpoint
  api: ApiEntity | undefined
  linkedServiceIds: Set<string>
  onLinked: (link: EndpointServiceLink) => void
}) {
  const titleId = useId()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const { data: componentsPage } = useAsync(() => componentsApi.list({ pageSize: 100 }), [])
  const components = componentsPage?.page.objectList ?? []
  const selectedComponent = components.find((component) => component.id === selectedId)

  const apiRef = api ? `api:${api.metadata.name}` : null
  const willCreateConsumesApi = Boolean(
    selectedComponent && apiRef && !selectedComponent.spec.consumesApis.includes(apiRef),
  )

  useEffect(() => {
    if (open) {
      setSelectedId(null)
      setSubmitError(null)
    }
  }, [open])

  async function handleSubmit() {
    if (!selectedId) return
    setSubmitting(true)
    setSubmitError(null)
    try {
      const link = await endpointServicesApi.link(endpoint.id, selectedId)
      onLinked(link)
      onClose()
    } catch (err) {
      setSubmitError(errorMessage(err, 'Failed to link service'))
    } finally {
      setSubmitting(false)
    }
  }

  const options = components.map((component) => {
    const alreadyLinked = linkedServiceIds.has(component.id)
    const name = component.metadata.title || component.metadata.name
    return {
      value: component.id,
      disabled: alreadyLinked,
      text: name,
      content: (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', gap: 8 }}>
          <span>
            {name}
            <Text color="secondary" variant="caption-2"> · {refName(component.spec.owner)}</Text>
          </span>
          {alreadyLinked && <Label size="xs">Already linked</Label>}
        </div>
      ),
    }
  })

  return (
    <Dialog open={open} onClose={onClose} aria-labelledby={titleId}>
      <Dialog.Header caption="Link service" id={titleId} />
      <Dialog.Body>
        <Select
          placeholder="Select a service…"
          filterable
          filterPlaceholder="Search services…"
          value={selectedId ? [selectedId] : []}
          onUpdate={(next) => setSelectedId(next[0] ?? null)}
          options={options}
          width="max"
        />
        {willCreateConsumesApi && api && (
          <Text color="secondary" style={{ display: 'block', marginTop: 12 }}>
            Linking will also mark {selectedComponent!.metadata.title || selectedComponent!.metadata.name} as consuming {api.metadata.title || api.metadata.name}.
          </Text>
        )}
      </Dialog.Body>
      <Dialog.Footer
        textButtonApply="Link"
        textButtonCancel="Cancel"
        onClickButtonCancel={onClose}
        onClickButtonApply={handleSubmit}
        loading={submitting}
        errorText={submitError ?? undefined}
        propsButtonApply={{ disabled: !selectedId }}
      />
    </Dialog>
  )
}
