## Why

A prerelease audit found `npm audit` reports 18 frontend vulnerabilities (6 high, 6 moderate, 6 low) — reconfirmed live in this change's investigation, same numbers. The high-severity findings sit directly in the Markdown/SVG rendering path used to show entity documentation (ReDoS in `linkify-it`/`markdown-it`, DoS and executable-content-sanitization bypasses in `svgo`, both via `@diplodoc/transform`), plus a CPU-DoS in `js-yaml` via `@redocly/openapi-core`. A public project asking users to paste untrusted Markdown/SVG/OpenAPI content into entity documentation and specs cannot ship with known DoS and sanitization-bypass CVEs sitting unpatched in that exact path. Separately, one frontend test is red: `LoginPage.test.tsx` asserts a button accessible name the component no longer renders — confirmed by running the suite, not just reading the audit's snapshot.

## What Changes

- Resolve or mitigate all 6 high-severity `npm audit` findings:
  - `js-yaml` (CPU DoS via unbounded merge keys), pulled in transitively by `@redocly/openapi-core` — update `@redocly/openapi-core` to a version that no longer depends on the vulnerable `js-yaml` range, or pin/override `js-yaml` if the upstream fix isn't yet released.
  - `linkify-it` (quadratic-complexity ReDoS, **no automatic fix available**) and `svgo` (Billion Laughs DoS plus three separate `removeScripts` sanitization-bypass advisories, **no automatic fix available**), both pulled in via `@diplodoc/transform` — no `@diplodoc/transform` release (checked through the latest 4.78.0) carries fixed versions, so both are pinned via a workspace `overrides` entry (`linkify-it@^5.0.2`, `svgo@3.3.5`), since `npm audit fix` cannot resolve these automatically.
  - `markdown-it`'s own two moderate ReDoS advisories (GHSA-38c4-r59v-3vqw, GHSA-6v5v-wf23-fmfq, fixed only at ≥14.2.0) are left unresolved: `@diplodoc/transform` and `@diplodoc/tabs-extension` both do CJS deep-imports (`require("markdown-it/lib/...")`) to reach `Token`/`utils`, which markdown-it's entire 14.x line no longer exposes (ESM-only internals, nothing equivalent re-exported from the public API) — forcing the bump breaks code-block syntax highlighting and the tabs extension. Documented as an accepted, unfixable-without-breakage risk; the two advisories are moderate, not high, so this doesn't block the zero-high-severity goal.
  - `uuid` (buffer-bounds-check bug) — no `@gravity-ui/markdown-editor` release fixes this (every recent release exact-pins the vulnerable `uuid@11.0.5`; `npm audit`'s suggested "fix" is a downgrade to a pre-vulnerability version, not a viable direction), so pin `uuid` to `11.1.1` directly via a workspace override, a same-major patch with no editor version change.
- Remove the direct, superseded `markdown-it` dependency if nothing in the frontend imports it directly once the Diplodoc chain is updated (audit before removing).
- Fix the failing `LoginPage.test.tsx` assertion: it expects the submit button's accessible name to be `Sign in with Username and password`, but `LoginPage.tsx` now renders a plain `Sign in` button for this flow — align the test with the current, intentional UI (single-provider forms no longer need the provider name in the button label; multi-provider forms still show `Sign in with {provider.displayName}` per `LoginPage.tsx:214`).
- Add hostile-input regression tests (adversarial Markdown, SVG with embedded scripts, deeply-nested/aliased YAML) against the entity-documentation and API-spec rendering paths, once the dependency chain is updated, so a future regression is caught by tests rather than another audit.
- **BREAKING**: none expected for end users; the `uuid` fix is a workspace override with no `@gravity-ui/markdown-editor` version change, but the override should still be smoke-tested against the existing Markdown editor UI before merging since it swaps a version the editor's own code was pinned to.
- Out of scope: wiring `npm audit --audit-level=high` into a CI gate — that belongs to the separately-proposed `harden-ci-and-supply-chain` change, since gate wiring should land once (and be sequenced against every change that needs to be green first), not duplicated here.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `markdown-entity-documentation`: rendering of an entity's or Flow's Markdown `documentation` must resist ReDoS in link/URL detection and must not allow SVG-embedded executable content to survive sanitization — currently implicit (assumed safe because Diplodoc "uses built-in sanitization," per the audit's own "already done well" list), this change makes it an explicit, tested requirement.
- `catalog-web-ui`: the Login page's credential-provider submit control's accessible name depends on whether the deployment offers one provider (plain `Sign in`) or multiple (`Sign in with {provider}`) — currently untested against the single-provider case, which is what broke.

## Impact

- `core/frontend/package.json` (removes the unused direct `markdown-it` dependency) and root `package.json`/`package-lock.json` (npm workspace root): `@redocly/openapi-core` update (carries a fixed `js-yaml` forward) plus workspace-level `overrides` pinning `linkify-it`, `svgo`, and `uuid` to fixed versions since `@diplodoc/transform` and `@gravity-ui/markdown-editor` have no upstream release that does so yet. `markdown-it` itself stays at 13.0.2 (see What Changes for why).
- `core/frontend/src/pages/LoginPage.test.tsx`: assertion fix.
- Any frontend code that renders Markdown documentation or SVG content from entity data (Overview tabs, Flow documentation, API spec viewers) — behavior should be unchanged for legitimate content, only hostile input handling changes.
- No backend/API changes.
