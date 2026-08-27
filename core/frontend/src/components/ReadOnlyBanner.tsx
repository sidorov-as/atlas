import { Alert } from '@gravity-ui/uikit'

/** Shown instead of Edit affordances on a YAML-managed entity's detail page (catalog-web-ui spec). */
export function ReadOnlyBanner({ ingestedFrom }: { ingestedFrom: string }) {
  return (
    <Alert
      theme="info"
      message={`managed by \`catalog-info.yaml\` in \`${ingestedFrom}\``}
    />
  )
}
