## Why

A prerelease security audit found that user-supplied entity content fields have no `max_length`/max-item-count constraints, creating storage DoS (unbounded rows) and client-side parsing/rendering DoS (frontend must handle arbitrarily large content). The audit cited `metadata.documentation`/description/labels/links (`plugin-api/python/atlas_plugin_api/schemas.py`) and inline API specs (`plugins/apis/backend/atlas_plugin_apis/api/schemas.py`). Investigating the actual schemas showed the gap is systemic, not limited to those two files: it also affects `DatabaseSchemaIn.source_sql` (`plugins/database-schema/backend/atlas_plugin_database_schema/schemas.py`) and `FlowIn.description`/`documentation`/`steps` (`plugins/flows/backend/atlas_plugin_flows/schemas.py`), which carry the same "unbounded free-text or list, attacker-controlled" shape.

## What Changes

- Add `max_length` to every unbounded free-text field on the shared entity metadata envelope (`MetadataIn`/`MetadataPatch` in `plugin-api/python/atlas_plugin_api/schemas.py`): `title`, `description`, `documentation`, and `LinkSchema`'s `url`/`title`/`description`/`type`. Limits are generous enough for real content (e.g. `documentation` is Markdown and may be long) but bounded.
- Add max-item-count to metadata list/dict fields: `labels` (dict), `tags` (list), `links` (list).
- Add a size bound to `ApiSpecIn.spec_content`/`ApiSpecPatch.spec_content` (inline API spec content) in `plugins/apis/backend/atlas_plugin_apis/api/schemas.py`. This covers only inline-provided spec content; a fetched-via-`specUrl` spec's size is bounded separately by the `fix-apis-ssrf` change's streaming/byte-cap fetch logic — this change does not duplicate that.
- Add a size bound to `DatabaseSchemaIn.source_sql`/`DatabaseSchemaPatch.source_sql` in `plugins/database-schema/backend/atlas_plugin_database_schema/schemas.py`.
- Add `max_length` to `FlowIn.description`/`documentation` and a max-item-count to `FlowIn.steps` in `plugins/flows/backend/atlas_plugin_flows/schemas.py`.
- All limits are enforced at the Pydantic schema layer (reject on create/patch), so they fail fast at the API boundary rather than only being caught later by storage or the frontend.

## Capabilities

### New Capabilities

None — these are bound tightenings on existing entity/field behavior, not new capabilities.

### Modified Capabilities

- `entity-catalog`: The entity envelope's `metadata` fields (`description`, `documentation`, `labels`, `tags`, `links`) currently accept unbounded content; this adds explicit size/count limits, rejecting oversized input at create/patch time.
- `api-spec-documents`: Inline (`spec_source: "inline"`) API spec content currently has no size limit; this adds one, enforced independently of the URL-source fetch limits being added by `fix-apis-ssrf`.
- `database-schema-plugin`: `source_sql` currently has no size limit; this adds one.
- `flow-management`: `Flow.description`/`documentation`/`steps` currently have no size/count limits; this adds them.

## Impact

- Touches Pydantic schema files across `plugin-api/python/atlas_plugin_api/`, `plugins/apis/backend/atlas_plugin_apis/api/`, `plugins/database-schema/backend/atlas_plugin_database_schema/`, and `plugins/flows/backend/atlas_plugin_flows/`.
- **BREAKING** for any existing content that already exceeds the new limits: a create/patch that previously succeeded may now be rejected. Existing stored rows are not truncated or migrated — only new writes are bounded. Chosen limits should be validated against realistic existing content sizes (e.g. longest current `documentation` value) before finalizing, to avoid breaking legitimate use.
- No database schema/migration changes expected (validation-layer only, not column-length changes) unless the chosen limits are later also enforced at the database column level.
