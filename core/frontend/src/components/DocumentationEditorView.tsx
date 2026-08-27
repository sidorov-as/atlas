import { useEffect } from 'react'
import { configure, MarkdownEditorView, useMarkdownEditor } from '@gravity-ui/markdown-editor'
import '@gravity-ui/markdown-editor/styles/styles.css'

configure({ lang: 'en' })

/** Isolates the hook-driven editor and exposes its serialised Markdown to form state. */
export default function DocumentationEditorView({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const editor = useMarkdownEditor({
    initial: { markup: value, mode: 'markup' },
    md: { html: false },
  }, [])

  useEffect(() => {
    const handleChange = () => onChange(editor.getValue())
    editor.on('change', handleChange)
    return () => editor.off('change', handleChange)
  }, [editor, onChange])

  useEffect(() => {
    if (editor.getValue() !== value) editor.replace(value)
  }, [editor, value])

  return <MarkdownEditorView editor={editor} stickyToolbar />
}
