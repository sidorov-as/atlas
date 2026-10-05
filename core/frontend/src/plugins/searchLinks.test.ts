// Routing coverage for `add-search-sources`: every link a plugin's search source returns must
// land on a route some installed plugin declares. The link shapes mirror `resolve` in
// `atlas_plugin_flows`, `atlas_plugin_apis` and `atlas_plugin_database_schema` search sources.
import { describe, expect, it } from 'vitest'
import { matchPath } from 'react-router-dom'
import { composedContributions } from './composition'

const ID = '3f6c0f5e-6a3e-4c53-9d5b-0a1b2c3d4e5f'

const links: [string, string, Record<string, string>][] = [
  ['flow', '/flows/42', { id: '42' }],
  ['endpoint', `/apis/${ID}/endpoints/${ID}`, { apiId: ID, endpointId: ID }],
  ['operation', `/apis/${ID}/operations/${ID}`, { apiId: ID, operationId: ID }],
  ['schema', `/resources/${ID}?tab=schema`, { id: ID }],
]

describe('search result links', () => {
  it.each(links)('a %s link matches exactly one declared route with its params', (_kind, link, params) => {
    const pathname = link.split('?')[0]
    const matches = composedContributions.routes
      .map((route) => matchPath({ path: route.path, end: true }, pathname))
      .filter((match) => match !== null)

    expect(matches).toHaveLength(1)
    expect(matches[0]?.params).toMatchObject(params)
  })

  it('routes the schema link to a resource detail page that has a schema tab', () => {
    const schemaTab = composedContributions.entityDetailTabs.find((tab) => tab.value === 'schema')

    expect(schemaTab).toBeDefined()
  })
})
