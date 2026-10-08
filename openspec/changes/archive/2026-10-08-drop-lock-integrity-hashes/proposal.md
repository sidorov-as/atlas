## Why

The lock file records a backend `hash` and a frontend `integrity` value for every plugin, but nothing reads them: not `validate`, not `generate`, not the Docker builds, not CI. Real integrity checking already happens one layer down, where `uv sync --frozen` and `npm ci` verify the native `uv.lock` and `package-lock.json`. For workspace plugins, which are all plugins today, the composer hashes source directories that arrive in the same commit as the lock, so the value protects nothing. It also makes every edit under `plugins/` rewrite `lock.yaml` in every distribution and example, burying real changes in diff noise.

## What Changes

- **BREAKING** Remove the backend `hash` and frontend `integrity` fields from the lock schema. A lock produced before this change no longer loads and must be re-resolved.
- Stop computing workspace-plugin directory hashes and delete the directory-hashing helper.
- Stop copying registry hashes out of `uv.lock` and `package-lock.json` into the lock. The composer keeps reading those files for the exact version and for the check that the manifest version matches.
- The lock remains the logical record of each plugin's backend and frontend package and exact version, plus disabled state, configuration, services and authentication policy, which generation consumes.
- Integrity of installed artifacts is delegated explicitly to the native lock files and the installers that verify them.
- Regenerate every `lock.yaml` (default distribution, Render deployment, examples).
- Update the manifest/lock reference, distributions guide, glossary, system-shape and troubleshooting docs that describe the lock as pinning integrity hashes.
- Add a CI check that re-resolving every distribution leaves no diff, so a stale lock is caught now that hash churn no longer makes that check noisy.

Out of scope: verifying artifacts at build time, supporting non-workspace artifact sources, and changing native lock handling.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `deployment-manifest-and-lock`: the requirement that the lock records integrity hashes becomes a requirement that it records exact versions and delegates integrity to the native lock files; add a requirement that a lock re-resolved from an unchanged manifest and unchanged native locks is identical.

## Impact

- `composer/atlas_composer`: `lock.py`, `resolver.py`, `uv_lock.py`, `npm_lock.py`, `_hashing.py` (removed) and their tests.
- All `lock.yaml` files under `distributions/`, `deploy/render/` and `examples/`.
- `docs-site` pages that describe lock contents.
- `.github/workflows`: new lock freshness check.
- Third-party tooling that reads `hash` or `integrity` from `lock.yaml` would break; none exists in this repository.
