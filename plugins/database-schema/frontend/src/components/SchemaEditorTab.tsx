// The facet editor: a dialect select plus a SQL input, matching the
// endpoint's own shape. Saves through the plugin-owned
// facet endpoint, never through Resource's own CRUD API.
import { useEffect, useState } from 'react'
import { Alert, Button, Loader, Select, Text } from '@gravity-ui/uikit'
import { CodeEditor } from 'frontend/components/CodeEditor'
import { errorMessage } from 'frontend/lib/api'
import { useAsync } from 'frontend/lib/useAsync'
import { useSession } from 'frontend/lib/SessionContext'
import type { CatalogEntityUnion } from 'frontend/lib/types'
import { databaseSchemaApi, isNoFacetFound, type DatabaseSchemaDialect, type DatabaseSchemaFacet } from '../lib/databaseSchemaApi'
import { ParseStatusIndicator } from './ParseStatusIndicator'

const DIALECT_OPTIONS: { value: DatabaseSchemaDialect, content: string }[] = [
  { value: 'postgresql', content: 'PostgreSQL' },
  { value: 'mysql', content: 'MySQL' },
  { value: 'mssql', content: 'MS SQL' },
]

export function SchemaEditorTab({ entity }: { entity: CatalogEntityUnion }) {
  // Administrative and custom mutation controls obey
  // read-only — this tab has no other client-side write gate (backend's `resource.edit`
  // check is the real boundary).
  const { session } = useSession()
  const isReadOnly = Boolean(session?.isReadOnly)
  const { data: facet, isLoading, error } = useAsync<DatabaseSchemaFacet | null>(
    () => databaseSchemaApi.get(entity.id).catch((err: unknown) => {
      if (isNoFacetFound(err)) return null
      throw err
    }),
    [entity.id],
  )

  const [sourceSql, setSourceSql] = useState('')
  const [dialect, setDialect] = useState<DatabaseSchemaDialect>('postgresql')
  const [saved, setSaved] = useState<DatabaseSchemaFacet | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  // Seeds the draft from whatever's already persisted — once per load, not on
  // every keystroke (`saved` tracks the load/save baseline separately from `sourceSql`).
  useEffect(() => {
    if (!isLoading) {
      setSourceSql(facet?.sourceSql ?? '')
      setDialect(facet?.dialect ?? 'postgresql')
      setSaved(facet)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoading, facet])

  if (isLoading) return <Loader size="m" />
  if (error) return <Alert theme="danger" message={errorMessage(error, 'Failed to load the database schema')} />

  async function handleSave() {
    setIsSaving(true)
    setSaveError(null)
    try {
      const result = saved
        ? await databaseSchemaApi.update(entity.id, sourceSql, dialect)
        : await databaseSchemaApi.create(entity.id, sourceSql, dialect)
      setSaved(result)
    } catch (err) {
      setSaveError(errorMessage(err, 'Failed to save the schema'))
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, maxWidth: 760 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <Text variant="subheader-2">Database schema</Text>
        {saved && <ParseStatusIndicator status={saved.parseStatus} />}
      </div>
      <Text color="secondary">
        Paste the `CREATE TABLE` statements that describe this Resource's schema. Saved SQL backs the ER Diagram tab.
      </Text>
      {isReadOnly ? (
        <>
          <Text color="secondary">Dialect: {DIALECT_OPTIONS.find((option) => option.value === dialect)?.content ?? dialect}</Text>
          <pre style={{ margin: 0, padding: 12, border: '1px solid var(--g-color-line-generic)', borderRadius: 8, overflowX: 'auto' }}>
            {sourceSql || 'No schema saved yet'}
          </pre>
        </>
      ) : (
        <>
          <div>
            <Text color="secondary">Dialect</Text>
            <Select
              value={[dialect]}
              onUpdate={(value) => setDialect(value[0] as DatabaseSchemaDialect)}
              options={DIALECT_OPTIONS}
              width={200}
            />
          </div>
          <CodeEditor value={sourceSql} onChange={setSourceSql} language="sql" />
          {saveError && <Alert theme="danger" message={saveError} />}
          <div>
            <Button view="action" loading={isSaving} onClick={() => void handleSave()}>
              Save schema
            </Button>
          </div>
        </>
      )}
    </div>
  )
}
