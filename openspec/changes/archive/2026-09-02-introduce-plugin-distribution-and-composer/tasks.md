## 1. Monorepo restructuring

- [x] 1.1 Move core backend/frontend code into `core/{backend,frontend}`, mechanically preserving import paths where possible.
- [x] 1.2 Move `atlas-plugin-api-python`/`@atlas/plugin-api` contract packages into `plugin-api/{python,typescript}`.
- [x] 1.3 Move each existing plugin (standard-catalog, apis, c4, database-schema, ingestion) into `plugins/<name>/`. Note: `auth-local`/`auth-oidc` are not separate plugin packages today — `introduce-auth-provider-extension` implemented `AuthenticationProvider`/`PolicyEvaluator`/OIDC directly inside `core/backend`'s catalog app. They stay part of Authentication Core for this change; extracting them into standalone plugin packages is deferred to a follow-up decision, not part of this mechanical move.
- [x] 1.4 Run the full test suite against the restructured layout with zero logic changes; fix only import paths.

## 2. Manifest and lock

- [x] 2.1 Define the manifest YAML schema (distribution id/version, core version, plugins[], auth providers/default, ui disable/order).
- [x] 2.2 Define the lock file schema (exact versions + hashes/integrity per plugin).
- [x] 2.3 Implement the composer's manifest → lock resolution step, reusing native pip/uv and npm lock mechanisms where possible.

## 3. Generation and validation

- [x] 3.1 Implement lock → `INSTALLED_APPS` generation, replacing `SELECTED_PLUGINS`.
- [x] 3.2 Implement lock → frontend `installedFrontendPlugins` module generation, replacing the hand-edited module.
- [x] 3.3 Implement each composition-validation rule from `composition-validation` with a dedicated synthetic-fixture test.

## 4. Configuration and secrets

- [x] 4.1 Define the plugin configuration schema contract (Pydantic backend models, matching TypeScript public-projection types).
- [x] 4.2 Implement central secret resolution (`fromEnv` references), excluded from lock file, frontend bundle, and public bootstrap response.
- [x] 4.3 Migrate `atlas.auth.oidc`'s configuration onto the new schema/secret mechanism.
- [x] 4.4 Add a test asserting no secret value appears in the lock file, frontend bundle, or public config response.

## 5. CI and default distribution

- [x] 5.1 Add Python import-boundary CI checks (plugin → plugin-api allowed; plugin → core internals forbidden; plugin → plugin forbidden except via contract package).
- [x] 5.2 Add the equivalent TypeScript import-boundary checks.
- [x] 5.3 Build `distributions/default/` as a real manifest selecting every first-party plugin; generate its lock file.
- [x] 5.4 Verify the composer-built default distribution passes every existing spec-scenario suite end-to-end.
