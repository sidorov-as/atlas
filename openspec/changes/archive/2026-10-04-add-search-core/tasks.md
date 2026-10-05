## 1. Contract (plugin API, Python)

- [x] 1.1 Define document, hit, source and engine types, capability flags and the response of `resolve`
- [x] 1.2 Add registries and `register_search_source` / `register_search_engine` following the authentication-provider registration pattern, including duplicate-id detection
- [x] 1.3 Write the engine conformance suite as importable tests for adapter authors
- [x] 1.4 Unit-test registration with and without a consuming plugin
- [x] 1.5 Enforce the configurable body-size bound with word-boundary truncation and a warning log

## 2. Composition

- [x] 2.1 Choose the engine at search-plugin startup from the registered engines (optional `engine` setting matched against the registration owner) and have composition check that an explicitly named engine plugin is selected and not disabled
- [x] 2.2 Test none / one / two engines with and without `engine`, a mismatching `engine`, a disabled engine plugin, and engine-without-search

## 3. Search plugin backend

- [x] 3.1 Scaffold the search plugin package, descriptor, config schema (including the optional `engine` setting) and app with migrations
- [x] 3.2 Add pending-change and status models
- [x] 3.3 Connect signals for registered sources' watched models and record pending changes on commit, de-duplicated
- [x] 3.4 Implement the drain job (batch, load documents, upsert/delete, remove pending only on success, record errors)
- [x] 3.5 Implement the rebuild job and the reindex management command
- [x] 3.6 Contribute both jobs through the scheduler job-registration hook and declare their ids
- [x] 3.7 Implement the search endpoint: query validation, engine query, grouping by source, resolve, over-fetch loop, pagination
- [x] 3.8 Implement core snippet generation with safe output and engine-highlight override
- [x] 3.9 Implement the status endpoint with limited and full detail
- [x] 3.10 Keep everything inert when the plugin is not selected or is disabled
- [x] 3.11 Make drain (default 10 s) and rebuild (default 6 h) intervals configurable and use the interval-job helper
- [x] 3.12 Run one rebuild at scheduler start when the engine is empty and sources are not

## 4. Postgres engine plugin

- [x] 4.1 Scaffold the plugin, descriptor and migration for the index table with vector and index
- [x] 4.2 Implement upsert, delete, query with title weighting and safe query parsing, health
- [x] 4.3 Implement atomic replace-all
- [x] 4.4 Run the conformance suite in the plugin's tests

## 5. Catalog source

- [x] 5.1 Implement the catalog source: documents, watched models, id mapping, state handling
- [x] 5.2 Implement `resolve` using existing entity read rules
- [x] 5.3 Register the source from the catalog's runtime hook
- [x] 5.4 Test removal, revival and permission-filtered results

## 6. Frontend contract and shell

- [x] 6.1 Add the single-occupant search contribution type and composition validation to the TypeScript plugin API
- [x] 6.2 Render the contribution in the application shell and nothing when absent
- [x] 6.3 Test composition conflict and absent-plugin behaviour

## 7. Search frontend plugin

- [x] 7.1 Scaffold the plugin and the search box in the shell
- [x] 7.2 Build the dialog with debounced querying, results with kind label and snippet, empty and unavailable states
- [x] 7.3 Add the keyboard shortcut (registered and removed by the search component itself), arrow/enter/escape navigation and navigation to the result link
- [x] 7.4 Render all text safely and test with markup in titles
- [x] 7.5 Check the import-boundary test still passes

## 8. Distribution and images

- [x] 8.1 Add both backend plugins and the frontend plugin to the default manifest and refresh the lock
- [x] 8.2 Verify startup, migrations and first rebuild in the containerized runtime
- [x] 8.3 Verify a distribution without search starts and shows no search UI
- [x] 8.4 Copy the new backend plugin sources (search, search engine for PostgreSQL) into the core backend image and the frontend plugin's manifest into the frontend build stage, and confirm the image builds
- [x] 8.5 Repeat 8.4 for the public demo image, which mirrors the core backend image

## 9. Public demo

- [x] 9.1 Add the search plugins to the demo manifest, regenerate its lock and generated plugin module with the existing demo script
- [x] 9.2 Run the reindex command in the demo's build step right after the demo catalog is seeded
- [x] 9.3 Verify the demo starts with no scheduler, search returns results on first request, and an edit shows a pending backlog in status
- [x] 9.4 Confirm the demo's memory use on the free plan is not materially affected

## 10. Documentation

- [x] 10.1 Write the architecture, index schema and indexing algorithm pages with diagrams
- [x] 10.2 Write the source and engine authoring guides and the operating page, including running without a scheduler and the prebuilt-index approach
- [x] 10.3 Add the pages to the site navigation and run the docs build checks

## 11. Verification

- [x] 11.1 Add end-to-end test: edit an entity, see it searchable after a drain, remove it, see it disappear
- [x] 11.2 Run the full local CI target and fix regressions
