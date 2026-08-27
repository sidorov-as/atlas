import { useMemo } from 'react'
import transform from '@diplodoc/transform'
import '@diplodoc/transform/dist/css/yfm.css'
import '@diplodoc/transform/dist/js/yfm'

/** Converts trusted, sanitized Markdown/YFM to interactive Diplodoc HTML. */
export default function DocumentationPreviewView({ value }: { value: string }) {
  const html = useMemo(
    () => transform(value, { lang: 'en', disableLiquid: true }).result.html,
    [value],
  )

  return <div className="yfm yfm_no-list-reset documentation-preview" dangerouslySetInnerHTML={{ __html: html }} />
}
