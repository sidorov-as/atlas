// Split from ApiSpecDocViewer so an OpenAPI doc never pulls in the AsyncAPI
// renderer's bundle (and its Node-only dependencies) at all, and vice versa.
import { RedocStandalone } from 'redoc'
import { useTheme } from 'frontend/lib/ThemeContext'
import { redocOptions } from './openApiTheme'
import './openApiDark.css'

export default function OpenApiViewer({ spec }: { spec: object }) {
  const { resolved } = useTheme()
  // Redoc reads its options once, so a theme change remounts it.
  return (
    <div className={resolved === 'dark' ? 'atlas-openapi-dark' : undefined}>
      <RedocStandalone key={resolved} spec={spec} options={redocOptions(resolved)} />
    </div>
  )
}
