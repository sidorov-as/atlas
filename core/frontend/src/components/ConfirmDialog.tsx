import { useId } from 'react'
import { Dialog, Text } from '@gravity-ui/uikit'
import type { ConfirmDialogProps } from '../lib/useConfirm'

/** Presentational confirm dialog driven by `useConfirm()`'s `dialogProps`. */
export function ConfirmDialog({
  open,
  title,
  message,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  preset = 'default',
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const titleId = useId()
  return (
    <Dialog open={open} onClose={onCancel} aria-labelledby={titleId}>
      <Dialog.Header caption={title} id={titleId} />
      <Dialog.Body>
        <Text>{message}</Text>
      </Dialog.Body>
      <Dialog.Footer
        preset={preset}
        textButtonApply={confirmText}
        textButtonCancel={cancelText}
        onClickButtonApply={onConfirm}
        onClickButtonCancel={onCancel}
      />
    </Dialog>
  )
}
