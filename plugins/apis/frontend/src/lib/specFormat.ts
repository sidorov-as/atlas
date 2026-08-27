// Client-side helpers for the inline spec editor.
// `spec_content` has no stored format discriminator, so both language
// selection and validity checking work from the raw text alone.
import { load as parseYaml } from 'js-yaml'

/** Leading-character sniff only — picks Monaco's tokenizer, never gates validity. */
export function detectSpecLanguage(content: string): 'json' | 'yaml' {
  const trimmed = content.trim()
  return trimmed.startsWith('{') || trimmed.startsWith('[') ? 'json' : 'yaml'
}

/** Same YAML-or-JSON-tolerant parse path as `ApiSpecDocViewer`. Returns a parse error message, or `null` when valid. */
export function parseSpecContent(content: string): string | null {
  try {
    parseYaml(content)
    return null
  } catch (err) {
    return err instanceof Error ? err.message : 'Invalid content'
  }
}
