// Link Service dialog for an Operation — service
// search/select (the operation's own `apiProvidedBy` Service excluded;
// already-linked service+role pairs shown disabled
// with an "Already linked" marker) plus a role picker (`publisher`/
// `subscriber`, unlike `LinkServiceDialog`'s Endpoint counterpart which has
// no role concept at all). Never rendered for a
// `removed` operation — the caller (OperationLinkedServicesTab) doesn't
// offer the trigger at all in that state.
import { useEffect, useId, useState } from 'react'
import { Dialog, Label, SegmentedRadioGroup, Select, Text } from '@gravity-ui/uikit'
import { errorMessage } from 'frontend/lib/api'
import { componentsApi } from 'frontend/lib/entities'
import { refName } from 'frontend/lib/types'
import { useAsync } from 'frontend/lib/useAsync'
import { operationServicesApi } from '../lib/entities'
import type { Operation, OperationRole, OperationServiceLink } from '../lib/types'

const ROLE_OPTIONS: { value: OperationRole, content: string }[] = [
  { value: 'publisher', content: 'Publisher' },
  { value: 'subscriber', content: 'Subscriber' },
]

export function LinkOperationServiceDialog({
  open,
  onClose,
  operation,
  linkedServiceRolePairs,
  onLinked,
}: {
  open: boolean
  onClose: () => void
  operation: Operation
  /** Every currently-linked `(serviceId, role)` pair for this operation, keyed as `${serviceId}:${role}` — used to disable already-linked options (that exact role) rather than the whole service. */
  linkedServiceRolePairs: Set<string>
  onLinked: (link: OperationServiceLink) => void
}) {
  const titleId = useId()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [role, setRole] = useState<OperationRole>('subscriber')
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const { data: componentsPage } = useAsync(() => componentsApi.list({ pageSize: 100 }), [])
  // The Operation's own document-owner Service is never linked through
  // `ServiceOperationUsage` — its role is already implied by `direction`
  // so it's excluded from the picker entirely.
  const providerServiceId = operation.provider?.service.id
  const components = (componentsPage?.page.objectList ?? []).filter((component) => component.id !== providerServiceId)

  useEffect(() => {
    if (open) {
      setSelectedId(null)
      setRole('subscriber')
      setSubmitError(null)
    }
  }, [open])

  const selectedAlreadyLinked = Boolean(selectedId && linkedServiceRolePairs.has(`${selectedId}:${role}`))

  async function handleSubmit() {
    if (!selectedId || selectedAlreadyLinked) return
    setSubmitting(true)
    setSubmitError(null)
    try {
      const link = await operationServicesApi.link(operation.id, selectedId, role)
      onLinked(link)
      onClose()
    } catch (err) {
      setSubmitError(errorMessage(err, 'Failed to link service'))
    } finally {
      setSubmitting(false)
    }
  }

  const options = components.map((component) => {
    const alreadyLinked = linkedServiceRolePairs.has(`${component.id}:${role}`)
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
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div>
            <Text color="secondary" style={{ display: 'block', marginBottom: 4 }}>Role</Text>
            <SegmentedRadioGroup value={role} onUpdate={(value) => setRole(value as OperationRole)} options={ROLE_OPTIONS} />
          </div>
          <div>
            <Text color="secondary" style={{ display: 'block', marginBottom: 4 }}>Service</Text>
            <Select
              placeholder="Select a service…"
              filterable
              filterPlaceholder="Search services…"
              value={selectedId ? [selectedId] : []}
              onUpdate={(next) => setSelectedId(next[0] ?? null)}
              options={options}
              width="max"
            />
          </div>
          {selectedAlreadyLinked && (
            <Text color="danger">This service is already linked with this role.</Text>
          )}
        </div>
      </Dialog.Body>
      <Dialog.Footer
        textButtonApply="Link"
        textButtonCancel="Cancel"
        onClickButtonCancel={onClose}
        onClickButtonApply={handleSubmit}
        loading={submitting}
        errorText={submitError ?? undefined}
        propsButtonApply={{ disabled: !selectedId || selectedAlreadyLinked }}
      />
    </Dialog>
  )
}
