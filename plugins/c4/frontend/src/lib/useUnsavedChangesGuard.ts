import { useCallback, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useConfirm } from 'frontend/lib/useConfirm'

/**
 * Asks before leaving a page with unsaved changes. The app uses a plain `BrowserRouter`, which has
 * no route blocker, so this covers what can be intercepted: closing or reloading the tab
 * (`beforeunload`), clicks on in-app links (a capturing click listener that confirms first), and the
 * page's own Cancel through `leave`. The browser Back button cannot be intercepted this way.
 *
 * Render `<ConfirmDialog {...dialogProps} />` once. Call `allowLeave()` right before navigating away
 * after a successful save.
 */
export function useUnsavedChangesGuard(dirty: boolean) {
  const navigate = useNavigate()
  const { confirm, dialogProps } = useConfirm()
  const dirtyRef = useRef(dirty)
  dirtyRef.current = dirty
  const bypass = useRef(false)

  const confirmLeave = useCallback(
    () =>
      dirtyRef.current && !bypass.current
        ? confirm({ title: 'Discard changes?', message: 'You have unsaved changes. If you leave now they will be lost.', confirmText: 'Leave', cancelText: 'Stay', preset: 'danger' })
        : Promise.resolve(true),
    [confirm],
  )

  const leave = useCallback(
    async (to: string) => {
      if (!(await confirmLeave())) return
      bypass.current = true
      navigate(to)
    },
    [confirmLeave, navigate],
  )

  const allowLeave = useCallback(() => { bypass.current = true }, [])

  useEffect(() => {
    const onBeforeUnload = (event: BeforeUnloadEvent) => {
      if (!dirtyRef.current || bypass.current) return
      event.preventDefault()
      event.returnValue = ''
    }
    const onClick = (event: MouseEvent) => {
      if (!dirtyRef.current || bypass.current || event.defaultPrevented) return
      if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
      const anchor = (event.target as Element | null)?.closest?.('a[href]') as HTMLAnchorElement | null
      if (!anchor || (anchor.target && anchor.target !== '_self') || anchor.origin !== window.location.origin) return
      const destination = `${anchor.pathname}${anchor.search}${anchor.hash}`
      if (destination === `${window.location.pathname}${window.location.search}${window.location.hash}`) return
      event.preventDefault()
      event.stopPropagation()
      void confirmLeave().then((ok) => {
        if (!ok) return
        bypass.current = true
        navigate(destination)
      })
    }
    window.addEventListener('beforeunload', onBeforeUnload)
    document.addEventListener('click', onClick, true)
    return () => {
      window.removeEventListener('beforeunload', onBeforeUnload)
      document.removeEventListener('click', onClick, true)
    }
  }, [confirmLeave, navigate])

  return { dialogProps, leave, allowLeave }
}
