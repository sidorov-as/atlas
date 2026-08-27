import { useCallback, useRef, useState } from 'react'

export interface ConfirmOptions {
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  /** `danger` for permanent/irreversible actions, `default` otherwise. */
  preset?: 'default' | 'danger'
}

export interface ConfirmDialogProps extends ConfirmOptions {
  open: boolean
  onConfirm: () => void
  onCancel: () => void
}

/**
 * Promise-based replacement for `window.confirm()`: `confirm(options)` resolves `true` on
 * confirm and `false` on cancel/outside-click/Escape. `dialogProps` is spread onto
 * `<ConfirmDialog>`, which the caller renders once alongside the triggering action.
 */
export function useConfirm(): { confirm: (options: ConfirmOptions) => Promise<boolean>; dialogProps: ConfirmDialogProps } {
  const [options, setOptions] = useState<ConfirmOptions | null>(null)
  const resolveRef = useRef<((value: boolean) => void) | null>(null)

  const confirm = useCallback((nextOptions: ConfirmOptions) => {
    setOptions(nextOptions)
    return new Promise<boolean>((resolve) => {
      resolveRef.current = resolve
    })
  }, [])

  const settle = useCallback((value: boolean) => {
    setOptions(null)
    resolveRef.current?.(value)
    resolveRef.current = null
  }, [])

  const dialogProps: ConfirmDialogProps = {
    open: options !== null,
    title: options?.title ?? '',
    message: options?.message ?? '',
    confirmText: options?.confirmText,
    cancelText: options?.cancelText,
    preset: options?.preset,
    onConfirm: () => settle(true),
    onCancel: () => settle(false),
  }

  return { confirm, dialogProps }
}
