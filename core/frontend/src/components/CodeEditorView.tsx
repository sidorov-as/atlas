import { Editor, type Monaco } from '@monaco-editor/react'
import { Text, useThemeType } from '@gravity-ui/uikit'
import { activeCodeEditorTheme, defineCodeEditorThemes } from '../lib/codeEditorTheme'

export type CodeEditorLanguage = 'sql' | 'yaml' | 'json'

function handleBeforeMount(monaco: Monaco) {
  defineCodeEditorThemes(monaco)
}

/**
 * Generic Monaco wrapper — knows only `value`/`onChange`/`language` and an
 * optional caller-supplied `error` to display, no domain concepts. `useThemeType` is read only to force a re-render when Gravity
 * UI's resolved theme flips (e.g. a `system`-theme OS scheme change), so the
 * Monaco `theme` prop — resolved the same way as Flow's `activeFlowTheme` —
 * stays in sync without a DOM observer.
 */
export default function CodeEditorView({
  value,
  onChange,
  language,
  error,
}: {
  value: string
  onChange: (value: string) => void
  language: CodeEditorLanguage
  error?: string | null
}) {
  useThemeType()

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{ border: '1px solid var(--g-color-line-generic)', borderRadius: 8, overflow: 'hidden' }}>
        <Editor
          height={320}
          language={language}
          value={value}
          theme={activeCodeEditorTheme()}
          beforeMount={handleBeforeMount}
          onChange={(nextValue) => onChange(nextValue ?? '')}
          options={{ minimap: { enabled: false }, automaticLayout: true, scrollBeyondLastLine: false, tabSize: 2 }}
        />
      </div>
      {error && (
        <Text color="danger" style={{ display: 'block' }}>
          {error}
        </Text>
      )}
    </div>
  )
}
