// Edge-click modal for the Visual canvas editor: edits or deletes one source->target transition without touching
// either endpoint step. Mirrors `FlowStepModal.tsx`'s `Dialog` structure.
import { useEffect, useId, useState } from 'react'
import { Button, Dialog, Text, TextInput } from '@gravity-ui/uikit'

export interface FlowTransitionModalProps {
  /** `null` closes the dialog and means no transition is currently selected. */
  transition: { sourceId: string; targetId: string; label?: string } | null
  onClose: () => void
  onSave: (sourceId: string, targetId: string, label: string) => void
  onDelete: (sourceId: string, targetId: string) => void
}

/** Edit-label / delete modal for a single canvas edge. */
export function FlowTransitionModal({ transition, onClose, onSave, onDelete }: FlowTransitionModalProps) {
  const titleId = useId()
  const [label, setLabel] = useState('')

  useEffect(() => {
    if (!transition) return
    setLabel(transition.label ?? '')
  }, [transition])

  function handleSave() {
    if (!transition) return
    onSave(transition.sourceId, transition.targetId, label)
    onClose()
  }

  function handleDelete() {
    if (!transition) return
    onDelete(transition.sourceId, transition.targetId)
    onClose()
  }

  return (
    <Dialog open={transition !== null} onClose={onClose} aria-labelledby={titleId} size="s">
      <Dialog.Header caption="Edit transition" id={titleId} />
      <Dialog.Body>
        <div style={{ display: 'grid', gap: 12 }}>
          {transition && (
            <Text color="secondary" variant="caption-2">{transition.sourceId} → {transition.targetId}</Text>
          )}
          <div>
            <Text color="secondary">Label</Text>
            <TextInput value={label} onUpdate={setLabel} placeholder="Label (optional)" autoFocus />
          </div>
        </div>
      </Dialog.Body>
      <Dialog.Footer
        textButtonApply="Save"
        textButtonCancel="Cancel"
        onClickButtonCancel={onClose}
        onClickButtonApply={handleSave}
      >
        <Button view="flat-danger" onClick={handleDelete}>Delete transition</Button>
      </Dialog.Footer>
    </Dialog>
  )
}
