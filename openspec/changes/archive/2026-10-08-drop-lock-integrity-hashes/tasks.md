## 1. Composer schema and resolution

- [x] 1.1 Remove `hash` from `LockedBackendArtifact` and `integrity` from `LockedFrontendArtifact` in `composer/atlas_composer/lock.py`; update the module docstring
- [x] 1.2 Make `load_lock` report a lock that still carries `hash` or `integrity` with a message telling the operator to re-resolve from the manifest
- [x] 1.3 Reduce `uv_lock.py` and `npm_lock.py` to name→version maps; drop hash and integrity handling and the `_hashing` import
- [x] 1.4 Update `resolver.py` to stop setting hash/integrity, including the path-based fallback, keeping the version and name checks
- [x] 1.5 Delete `composer/atlas_composer/_hashing.py` and `tests/test_hashing.py`

## 2. Tests

- [x] 2.1 Remove `hash`/`integrity` arguments from lock fixtures in `test_lock.py`, `test_generate.py`, `test_descriptors.py`, `test_config_isolation.py`, `test_services.py` and `test_resolver.py`
- [x] 2.2 Replace hash assertions in `test_uv_lock.py` and `test_npm_lock.py` with version-resolution assertions
- [x] 2.3 Add a test that a lock with legacy `hash`/`integrity` fields fails to load with the re-resolve message
- [x] 2.4 Add a test that resolving twice after editing a workspace plugin source file yields an identical lock
- [x] 2.5 Run the composer test suite and the backend tests that load distribution locks

## 3. Regenerate locks

- [x] 3.1 Run `make lock` to regenerate every `lock.yaml` under `distributions/`, `deploy/render/` and `examples/`
- [x] 3.2 Confirm the diff only removes `hash`/`integrity` lines, then run `make lock-validate`

## 4. CI

- [x] 4.1 Add a workflow step that runs `make lock` and fails if `git diff --exit-code` reports changes to any `lock.yaml`
- [x] 4.2 Verify the step passes on this branch and fails when a manifest is edited without re-resolving

## 5. Documentation

- [x] 5.1 Update `docs-site/docs/configuration/distributions.md` and `docs-site/docs/reference/distribution-manifest.md` to show the lock without `hash`/`integrity`
- [x] 5.2 Update `docs-site/docs/concepts/glossary.md`, `concepts/system-shape.md`, `operating-atlas/composition-errors.md` and `deployment/troubleshooting.md` to say integrity comes from `uv.lock` and `package-lock.json`
- [x] 5.3 Run `openspec validate drop-lock-integrity-hashes`
