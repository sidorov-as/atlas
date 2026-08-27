// Database Schema frontend plugin — the schema editor
// and ER Diagram tab contributions on Resource's detail page, matching
// `@atlas/plugin-standard-catalog`, `@atlas/plugin-apis`, and `@atlas/plugin-c4`'s
// independent package boundary.
import { defineFrontendPlugin } from '@atlas/plugin-api'
import { databaseSchemaEntityDetailTabs } from './entityDetailTabs'

export const databaseSchemaPlugin = defineFrontendPlugin({
  id: 'atlas.database-schema',
  contributions: [...databaseSchemaEntityDetailTabs],
})
