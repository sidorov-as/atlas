// Data-fetching wrapper around `ErDiagramView`. The tab button itself
// is gated purely on `entitySupports('schema.host.v1')` —
// per-instance facet presence can't gate `entityDetailTab.when`, since `when` is
// a synchronous check over the entity payload and the facet deliberately isn't
// part of it. Absence/failure is handled here instead, as
// an in-tab empty/failure state rather than hiding the tab.
import { Alert, Loader, Text } from '@gravity-ui/uikit'
import { errorMessage } from 'frontend/lib/api'
import { useAsync } from 'frontend/lib/useAsync'
import type { CatalogEntityUnion } from 'frontend/lib/types'
import { databaseSchemaApi, isNoFacetFound, type DatabaseSchemaFacet } from '../lib/databaseSchemaApi'
import { ErDiagramView } from './ErDiagramView'

export function ErDiagramTab({ entity }: { entity: CatalogEntityUnion }) {
  const { data: facet, isLoading, error } = useAsync<DatabaseSchemaFacet | null>(
    () => databaseSchemaApi.get(entity.id).catch((err: unknown) => {
      if (isNoFacetFound(err)) return null
      throw err
    }),
    [entity.id],
  )

  if (isLoading) return <Loader size="m" />
  if (error) return <Alert theme="danger" message={errorMessage(error, 'Failed to load the database schema')} />
  if (!facet) {
    return <Text color="secondary">No database schema is attached to this Resource yet. Add one on the Schema tab.</Text>
  }
  if (facet.parseStatus !== 'ok') {
    return <Alert theme="danger" title="The saved SQL failed to parse" message="No ER Diagram can be rendered yet. Fix the SQL on the Schema tab." />
  }
  return <ErDiagramView schema={facet.parsedSchema} />
}
