## 1. Baseline data check

- [x] 1.1 Query current max observed lengths/counts for `metadata.description`, `metadata.documentation`, `metadata.labels`, `metadata.tags`, `metadata.links` across existing entities.
- [x] 1.2 Query current max observed length for `ApiSpecIn.spec_content` (inline-sourced APIs only).
- [x] 1.3 Query current max observed length for `DatabaseSchemaIn.source_sql`.
- [x] 1.4 Query current max observed length/count for `FlowIn.description`, `documentation`, `steps`.
- [x] 1.5 Pick final numeric limits for each field, comfortably above the observed maximums from 1.1-1.4.

  No production data exists (OSS project); checked the seeded demo catalog (`seed_booking_demo`) instead, the closest available data. Observed maximums: `metadata.description` 80 chars, `metadata.documentation` 1206 chars, `metadata.labels` 0 entries, `metadata.tags` 4 entries, `metadata.links` 0 entries, `ApiSpecIn.spec_content` (inline) 7227 chars, `DatabaseSchemaIn.source_sql` 958 chars, `Flow.description` 98 chars, `Flow.documentation` 537 chars, `Flow.steps` 9 entries.

  Chosen limits (generous headroom):
  - `MetadataIn`/`MetadataPatch.title`: 255 (matches `CatalogEntity.title`'s existing DB `CharField(max_length=255)`)
  - `description` (metadata, link, flow): 4096
  - `documentation` (metadata, flow): 1,048,576 (1 MiB)
  - `labels`: max 100 entries; `tags`: max 100 entries; `links`: max 50 entries
  - `LinkSchema.url`: 2048; `LinkSchema.title`: 255; `LinkSchema.type`: 64
  - `ApiSpecIn.spec_content` (inline): 2,097,152 (2 MiB) — see note below
  - `DatabaseSchemaIn.source_sql`: 2,097,152 (2 MiB) — see note below
  - `FlowIn.steps`: max 500 entries

  **Correction found during implementation (task 3):** Django's default, unconfigured `DATA_UPLOAD_MAX_MEMORY_SIZE` is 2.5 MiB and applies to the *entire* request body ahead of any Pydantic validation. An initial `spec_content` choice of 20 MiB (matching `fix-apis-ssrf`'s URL-fetch byte cap, for consistency across the field's two sources) turned out to be unreachable: a request that large is killed by Django first, as an unhandled/unattributed 422 — violating task 6.2's "clear, field-attributed error" requirement. `spec_content` (inline) and `source_sql` were both set to 2 MiB instead, safely under that ceiling; `documentation` (1 MiB) was already safely under it. The `url`-sourced path is unaffected — it bypasses the request body entirely (`spec_fetch.resolve_api_spec_url` writes fetched content straight onto the model) and stays bounded by its own, more generous, 20 MiB `MAX_SPEC_RESPONSE_BYTES` cap. Left Django's global setting untouched rather than raising it, to keep this change scoped to the specific fields and avoid loosening an existing app-wide body-size guard.

## 2. Shared metadata envelope (plugin-api)

- [x] 2.1 Add `max_length` to `MetadataIn.title`/`description`/`documentation` and the matching fields on `MetadataPatch`, in `plugin-api/python/atlas_plugin_api/schemas.py`.
- [x] 2.2 Add a max-item-count validator to `MetadataIn.labels`/`tags`/`links` and the matching fields on `MetadataPatch`.
- [x] 2.3 Add `max_length` to `LinkSchema.url`/`title`/`description`/`type`.
- [x] 2.4 Add negative tests: oversized `description`, oversized `documentation`, too many `labels`, too many `tags`, too many `links`, oversized link field — each on both create and patch.

## 3. Inline API spec content

- [x] 3.1 Add `max_length` to `ApiSpecIn.spec_content` and `ApiSpecPatch.spec_content` in `plugins/apis/backend/atlas_plugin_apis/api/schemas.py`, scoped so it does not affect content populated by the URL-fetch path (which is bounded separately by `fix-apis-ssrf`).
- [x] 3.2 Add a negative test: creating/patching an API with `spec_source: inline` and oversized `spec_content` is rejected.
- [x] 3.3 Add a test confirming URL-sourced `spec_content` (populated server-side after fetch) is unaffected by this limit's create/patch-time validation.

## 4. Inline SQL (database-schema plugin)

- [x] 4.1 Add `max_length` to `DatabaseSchemaIn.source_sql` and `DatabaseSchemaPatch.source_sql` in `plugins/database-schema/backend/atlas_plugin_database_schema/api/schemas.py` (actual path has an `api/` segment tasks.md omitted).
- [x] 4.2 Add a negative test: oversized `source_sql` on create and patch is rejected.

## 5. Flow content fields

- [x] 5.1 Add `max_length` to `FlowIn.description`/`documentation` and matching `FlowPatch` fields, in `plugins/flows/backend/atlas_plugin_flows/api/schemas.py` (actual path has an `api/` segment tasks.md omitted).
- [x] 5.2 Add a max-item-count validator to `FlowIn.steps` and `FlowPatch.steps`.
- [x] 5.3 Add negative tests: oversized `description`, oversized `documentation`, too many `steps` — on both create and patch.

## 6. Verification

- [x] 6.1 Run each affected plugin's backend test suite and confirm no existing legitimate fixture/test data is broken by the new limits.

  Ran `plugin-api`, `apis`, `database-schema`, `flows` (628 tests), plus `core/backend` catalog, `standard-catalog`, `c4`, `ingestion` (449 tests, excluding one pre-existing, unrelated `docker`-CLI-dependent integration test that can't run inside this container) — all pass, no existing fixtures broken.

- [x] 6.2 Confirm all new validators produce a clear, field-attributed error message (not a generic 500 or an unattributed validation failure).

  Verified all four: oversized `metadata.description` → `{"msg": "String should have at most 4096 characters", "loc": ["parsed_body", "metadata", "description"], ...}`; oversized inline `spec_content` → same shape at `spec.specContent`; oversized `source_sql` → same shape at `sourceSql`; too many `steps` → `{"msg": "List should have at most 500 items after validation, not 501", "loc": ["parsed_body", "steps"], ...}`. All HTTP 400, all field-attributed via `loc`, none a generic 500.

- [x] 6.3 Confirm `c4` and `standard-catalog` plugin schemas were re-checked and genuinely have no additional unbounded free-text/list fields beyond what this change already covers via the shared metadata envelope.

  `c4`'s `api/schemas.py` has no write (`*In`) schemas at all — only bounded literal/bool diagram query params. `standard-catalog`'s only free-text fields outside the metadata envelope are `ActorSpecIn.display_name`/`email`, which have no public CRUD endpoint (admin/ingestion-only, per that module's own docstring), matching design.md's stated non-goal. Ref-list fields (`provides_apis`, `consumes_apis`, `depends_on`, `members`) are unbounded in count but each entry must resolve to a real, already-existing catalog entity via `ref_list_validator` — not attacker-stuffable free text in a single request — so they don't share the audit's "unbounded free-text or list, attacker-controlled" shape.
