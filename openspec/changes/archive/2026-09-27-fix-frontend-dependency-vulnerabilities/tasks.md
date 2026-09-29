## 1. Baseline

- [x] 1.1 Run `npm audit` from the workspace root and record the current 18-vulnerability baseline (6 high, 6 moderate, 6 low) with advisory IDs.
- [x] 1.2 Run the full frontend test suite (`core/frontend` and any plugin frontends with tests) and record current pass/fail state as a baseline.

## 2. Dependency fixes

- [x] 2.1 Investigate available `@redocly/openapi-core` versions; upgrade to one that resolves the `js-yaml` CPU-DoS advisory (GHSA-2883-xcg3-v3hh), or pin `js-yaml` directly if no upstream release exists yet.
- [x] 2.2 Investigate available `@diplodoc/transform` versions; upgrade to one that resolves the `linkify-it`/`markdown-it` ReDoS advisories (GHSA-22p9-wv53-3rq4, GHSA-v245-v573-v5vm) and the `svgo` advisories (GHSA-xpqw-6gx7-v673, GHSA-2p49-hgcm-8545, GHSA-w27v-7q3p-w38r, GHSA-4vpr-x523-8j87).
- [x] 2.3 If no upstream fix is available for 2.2, add workspace-level `overrides`/`resolutions` pinning `linkify-it`, `markdown-it`, and `svgo` to fixed versions, and document that as a stopgap in the PR description.
- [x] 2.4 Evaluate and take the `@gravity-ui/markdown-editor` major bump (via `npm audit fix --force` or an explicit version bump) to resolve the `uuid` buffer-bounds-check advisory (GHSA-w5hq-g745-h8pq).
- [x] 2.5 Grep the frontend workspaces for direct `markdown-it` imports; remove the direct dependency if nothing imports it outside the Diplodoc chain, otherwise upgrade it in place.
- [x] 2.6 Re-run `npm audit`; confirm zero high-severity findings remain (moderate/low may remain if genuinely unfixable — document any that do, with rationale).

## 3. Test fix

- [x] 3.1 Update the assertion in `core/frontend/src/pages/LoginPage.test.tsx` to expect the button accessible name `Sign in` for the single local-credential-provider scenario it exercises.
- [x] 3.2 Run the full frontend test suite; confirm all tests pass.

## 4. Rendering regression verification

- [x] 4.1 Manually or via snapshot test, verify legitimate entity Markdown documentation (headings, lists, links) renders identically before and after the dependency bump.
- [x] 4.2 Smoke-test the Markdown editor UI (create/edit forms using `markdown-entity-documentation`) after the `@gravity-ui/markdown-editor` bump.
- [x] 4.3 Add a regression test with a link/URL pattern designed to trigger quadratic-complexity scanning in the Markdown link detector; confirm it renders without pathological slowdown.
- [x] 4.4 Add a regression test with an SVG containing an embedded `<script>`, a namespace/control-character-obfuscated executable link, and executable HTML inside `foreignObject`; confirm none execute or survive sanitization in the rendered output.
- [x] 4.5 Add a regression test with deeply-nested/aliased YAML (e.g. an OpenAPI spec with excessive anchors/merge keys) against the spec-loading path; confirm it is rejected or bounded rather than exhausting CPU/memory.

## 5. Final verification

- [x] 5.1 Run `npm audit` and confirm the result matches what's documented in task 2.6.
- [x] 5.2 Run the full frontend test and build pipeline; confirm no regressions versus the 1.2 baseline.
- [x] 5.3 Run `openspec validate fix-frontend-dependency-vulnerabilities` and confirm it passes.
