import { useEffect, useState } from 'react'
import { Magnifier } from '@gravity-ui/icons'
import { Button, Hotkey, Icon } from '@gravity-ui/uikit'
import { SearchDialog } from './SearchDialog'

/** The shell-level search control: a box that opens the results dialog, also bound to Cmd/Ctrl+K. */
export function SearchBox() {
  const [open, setOpen] = useState(false)

  // The shortcut belongs to this component: registered on mount, removed on unmount.
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && !event.altKey && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setOpen(true)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  return (
    <>
      <Button view="outlined" size="m" onClick={() => setOpen(true)} aria-label="Search" aria-keyshortcuts="Control+K Meta+K">
        <Icon data={Magnifier} size={16} />
        Search
        <Hotkey value="mod+k" style={{ marginLeft: 8 }} />
      </Button>
      <SearchDialog open={open} onClose={() => setOpen(false)} />
    </>
  )
}
