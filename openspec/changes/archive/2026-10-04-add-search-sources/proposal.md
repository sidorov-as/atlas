## Why

With global search in place for catalog entities, users still cannot find the other things Atlas holds: flows, API endpoints and operations, and database schemas. These belong to optional plugins with their own models and their own read rules, so each plugin has to describe what is searchable. Two of them (flows and the database schema facet) also have no audit timestamps, which makes their history hard to inspect.

## What Changes

- The flows plugin makes flows searchable by name, description and documentation, plus the visible text of their steps.
- The APIs plugin makes API endpoints and operations searchable (path or channel, summary, operation id). API entities themselves are already covered as catalog entities; raw specification text is not indexed.
- The database schema plugin makes each schema searchable through its table and column names; a hit leads to the owning resource's schema view.
- Each plugin's results respect that plugin's existing read rules.
- Search results for these sources reach users in the existing search dialog without UI changes, with a recognizable label per kind.
- Flows and the database schema facet gain `created_at` and `updated_at` timestamps, shown in the admin, for audit and history. Search does not depend on them.
- Each source works only when the search plugin is selected; without it, nothing changes for these plugins.

Out of scope: deep links into a flow node or a table, searching raw OpenAPI/AsyncAPI documents, incremental indexing from timestamps, any change to the search contract or UI, and exposing the new timestamps through public APIs.

## Capabilities

### New Capabilities
- `search-flow-source`: flows as searchable documents, their text, links and authorization.
- `search-api-source`: API endpoints and operations as searchable documents.
- `search-database-schema-source`: database schemas as searchable documents keyed to the owning resource.

### Modified Capabilities
- `flows-plugin`: flows record creation and last-modification times.
- `database-schema-plugin`: the schema facet records creation and last-modification times.

## Impact

- `plugins/flows`, `plugins/apis`, `plugins/database-schema`: each registers a source from its runtime hook; flows and the schema facet get a migration and admin display for the timestamps.
- Flows live under an existing catalog app label, so their migration is part of that app's history.
- No change to the search plugin, its engine adapters or the frontend.
- Depends on the search core change.
