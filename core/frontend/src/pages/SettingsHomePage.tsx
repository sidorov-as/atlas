import { useState } from 'react'
import { Alert, Button, Loader, Text } from '@gravity-ui/uikit'
import { DocumentationEditor } from '../components/DocumentationEditor'
import { DocumentationPreview } from '../components/DocumentationPreview'
import { errorMessage } from '../lib/api'
import { catalogHomeSettingsApi } from '../lib/entities'
import { useAsync } from '../lib/useAsync'
import { useSession } from '../lib/SessionContext'

/**
 * Editor body, mounted only once `initialAboutMarkdown` has loaded — lets
 * `aboutMarkdown`/`savedMarkdown` initialize directly from it instead of
 * syncing local state from an async result via an effect.
 */
function SettingsHomeEditor({ initialAboutMarkdown, isReadOnly }: { initialAboutMarkdown: string; isReadOnly: boolean }) {
  const [aboutMarkdown, setAboutMarkdown] = useState(initialAboutMarkdown)
  const [savedMarkdown, setSavedMarkdown] = useState(initialAboutMarkdown)
  const [isSaving, setIsSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [justSaved, setJustSaved] = useState(false)
  const isDirty = aboutMarkdown !== savedMarkdown

  async function handleSave() {
    setIsSaving(true)
    setSaveError(null)
    try {
      await catalogHomeSettingsApi.update(aboutMarkdown)
      setSavedMarkdown(aboutMarkdown)
      setJustSaved(true)
    } catch (err) {
      setSaveError(errorMessage(err, 'Failed to save'))
    } finally {
      setIsSaving(false)
    }
  }

  // catalog-web-ui spec's "Read-only administrator opens settings" — editing/saving controls
  // are absent for a read-only session even though `SettingsLayout` already requires isAdmin.
  if (isReadOnly) {
    return <DocumentationPreview value={aboutMarkdown} />
  }

  return (
    <>
      {saveError && <Alert theme="danger" message={saveError} />}
      <DocumentationEditor
        value={aboutMarkdown}
        onChange={(value) => { setAboutMarkdown(value); setJustSaved(false) }}
      />
      <div style={{ marginTop: 16, display: 'flex', alignItems: 'center', gap: 12 }}>
        <Button view="action" disabled={!isDirty} loading={isSaving} onClick={() => void handleSave()}>
          Save
        </Button>
        {justSaved && !isDirty && <Text color="positive">Saved</Text>}
      </div>
    </>
  )
}

/** Admin editor for the homepage's "About this catalog" Markdown (catalog-home-content spec). */
export function SettingsHomePage() {
  const { data, isLoading, error } = useAsync(() => catalogHomeSettingsApi.get(), [])
  const { session } = useSession()
  const isReadOnly = Boolean(session?.isReadOnly)

  return (
    <div>
      <Text variant="subheader-2">Home</Text>
      <p>
        <Text color="secondary">Edit the "About this catalog" section shown on the homepage</Text>
      </p>
      {error && <Alert theme="danger" message={error.message} />}
      {isLoading && !data ? (
        <Loader size="m" />
      ) : (
        <SettingsHomeEditor initialAboutMarkdown={data?.aboutMarkdown ?? ''} isReadOnly={isReadOnly} />
      )}
    </div>
  )
}
