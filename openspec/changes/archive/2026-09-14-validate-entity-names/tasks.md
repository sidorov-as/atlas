## 1. Shared name validator (plugin-api)

- [x] 1.1 In `plugin-api/python/atlas_plugin_api/schemas.py`, add `_validate_name(value: str) -> str` (strip, reject empty, reject `/` or `:`) plus `name_validator()`/`optional_name_validator()` factory functions, mirroring the existing `ref_validator`/`optional_ref_validator` style
- [x] 1.2 Apply `name_validator()` to `MetadataIn.name` and `optional_name_validator()` to `MetadataPatch.name` via `field_validator`
- [x] 1.3 Export `name_validator`/`optional_name_validator` from `plugin-api/python/atlas_plugin_api/schemas.py`'s `__all__` and re-export from `plugin-api/python/atlas_plugin_api/__init__.py`
- [x] 1.4 Add/update tests in `plugin-api/python/atlas_plugin_api/tests/test_schemas.py`: `MetadataIn` rejects `""`, `"   "`, a name containing `/`, a name containing `:`; `MetadataIn` strips `" checkout "` to `"checkout"`; `MetadataPatch` with `name` omitted keeps `model_fields_set` empty of `name` (no rejection); `MetadataPatch` with explicit invalid `name` is rejected

## 2. Flow's own name validator (flows plugin)

- [x] 2.1 In `plugins/flows/backend/atlas_plugin_flows/api/schemas.py`, import `name_validator`/`optional_name_validator` from `atlas_plugin_api` (alongside the existing `ref_validator`/`optional_ref_validator` import) and apply to `FlowIn.name` / `FlowPatch.name`
- [x] 2.2 Add/update tests in `plugins/flows/backend/atlas_plugin_flows/tests/test_flow_crud.py`: creating/updating a Flow with `""`, `"   "`, `/`-containing, or `:`-containing `name` is rejected; PATCH omitting `name` leaves it unchanged

## 3. Ingestion: drop the now-redundant manual check

- [x] 3.1 In `plugins/ingestion/backend/atlas_plugin_ingestion/validation.py`'s `validate_manifest_document`, remove the manual `if '/' in document.metadata.name: raise ManifestError(...)` block now that `MetadataIn`'s validator rejects it earlier via `ValidationError`
- [x] 3.2 Update/remove any ingestion test that asserted on the old hand-rolled `ManifestError` message for a `/`-containing name, replacing it with an assertion on the schema-level validation error if one exists (check `plugins/ingestion/backend/atlas_plugin_ingestion/tests/test_ingestion.py`) — verified: no existing test asserted on the old message, nothing to change

## 4. Docs

- [x] 4.1 Update `docs-site/docs/concepts/catalog-info-yaml.md`'s "Validation constraints" paragraph (and the inline `# required; must not contain "/"` comment) to also mention `:` and the empty/whitespace-only rejection

## 5. Frontend: required Name field

- [x] 5.1 Add `required` to the Name `TextInput` in `core/frontend/src/components/EntityFormShell.tsx`
- [x] 5.2 Add `required` to the Name `TextInput` in `plugins/flows/frontend/src/pages/FlowFormPage.tsx`
- [x] 5.3 Add a test case to `plugins/flows/frontend/src/pages/FlowFormPage.test.tsx` confirming the Name input is `required` (form does not call the save API when Name is left blank and submit is triggered)
- [x] 5.4 Add a focused test for `EntityFormShell`'s Name field being `required` — either a new `core/frontend/src/components/EntityFormShell.test.tsx` or a case added to one of the existing form-page tests that already exercise `EntityFormShell` (e.g. `plugins/standard-catalog/frontend/src/pages/SystemFormPage.test.tsx` if it exists, otherwise pick the nearest existing form-page test)

## 6. Verify

- [x] 6.1 Run the backend test suites touched above (`plugin-api`, `core/backend` catalog tests, `plugins/flows/backend`, `plugins/ingestion/backend`) and the frontend test suites touched above (`core/frontend`, `plugins/flows/frontend`) — all pass: 426 backend, 423 core/frontend, 185 flows/frontend
- [x] 6.2 Manually verify in the running app: attempting to submit System/Component/Resource/API/Flow create forms with an empty Name is blocked by the browser before any request is sent — verified via the running Docker Compose stack for the System form (EntityFormShell, shared by Component/Resource/API) and the Flow form: submitting with empty Name fired no API request; submitting with Name filled proceeded past the browser's native check to the next validation step
