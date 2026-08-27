import { Alert } from '@gravity-ui/uikit'

/**
 * Shown on an Unavailable Entity's detail page (unavailable-entity spec):
 * its kind currently has no active handler (the providing plugin is
 * disabled/removed), so kind-specific data isn't shown and edits are
 * rejected — identity and relations remain intact and are unaffected.
 */
export function UnavailableEntityBanner() {
  return (
    <Alert
      theme="warning"
      title="This entity is unavailable"
      message="Its kind's plugin isn't currently active, so kind-specific data can't be shown and edits are disabled. Re-enabling the plugin restores full access."
    />
  )
}
