## Context

The frontend is an npm workspace rooted at `/package.json` with member packages `core/frontend`, `plugin-api/typescript`, and five plugin frontends. `npm audit` run from the workspace root currently reports 18 vulnerabilities (6 high, 6 moderate, 6 low) — verified live during this change's investigation, matching the prerelease audit's snapshot exactly. The two "no automatic fix" high-severity chains (`linkify-it`/`markdown-it` ReDoS, `svgo` DoS/sanitization-bypass) both route through `@diplodoc/transform`, the Markdown rendering library used for entity `documentation` fields (`markdown-entity-documentation` capability). The `js-yaml` CPU-DoS chain routes through `@redocly/openapi-core`, used for OpenAPI spec handling. `uuid`'s fix is available only via `npm audit fix --force`, which would bump `@gravity-ui/markdown-editor` to a new major.

## Goals / Non-Goals

**Goals:**
- Zero high-severity `npm audit` findings in the dependency graph actually shipped to users.
- No silent behavior change to legitimate Markdown/SVG/OpenAPI content rendering.
- Regression tests that would have caught this class of issue before another audit has to find it.

**Non-Goals:**
- Wiring `npm audit` into CI as a required gate (belongs to `harden-ci-and-supply-chain`).
- General frontend dependency upgrades unrelated to the audit findings.
- Rewriting the Markdown/SVG rendering pipeline — this change patches/upgrades the existing Diplodoc-based pipeline, it doesn't replace it.

## Decisions

- **No `@diplodoc/transform` release picks up fixed sub-dependencies** (confirmed during implementation up to the latest 4.78.0: `svgo` and `markdown-it` are pinned to exact/narrow ranges in its own `package.json`). Fallback: workspace-level `overrides` pinning `linkify-it` and `svgo` directly to fixed versions.
- **Override `linkify-it` to `^5.0.2` but deliberately do NOT override `markdown-it`.** Investigation found that markdown-it's entire 14.x line (not just the latest release) restructured its internals to ESM-only `.mjs` files and stopped exporting `Token`/`utils` from its public API. `@diplodoc/transform`'s syntax-highlighting code (`lib/highlight.js`, `lib/plugins/code.js`, `lib/plugins/inline-code/index.js`) and `@diplodoc/tabs-extension` both do CJS deep-imports (`require("markdown-it/lib/...")`) to reach exactly those internals — forcing markdown-it to 14.x breaks code-block syntax highlighting and the tabs extension at both test-run and production-build time (verified: `DocumentationPreview.test.tsx` fails with `Cannot find module '.../markdown-it/lib/token'`). `linkify-it` has no such deep-import consumers and ships a stable CJS build at every checked version, so overriding it alone is safe.
- **Accept markdown-it's own two moderate ReDoS advisories (GHSA-38c4-r59v-3vqw, GHSA-6v5v-wf23-fmfq) as unfixed, with rationale documented in the PR.** Both require markdown-it ≥14.2.0, which is incompatible with `@diplodoc/transform`'s and `@diplodoc/tabs-extension`'s CJS deep-imports as described above. The `svgo` fix and `linkify-it` fix eliminate every HIGH-severity finding in this chain; these two markdown-it-own bugs are the only MODERATE findings left unresolved from the original audit, per the "moderate/low may remain if genuinely unfixable" allowance.
- **Pin `uuid` to `11.1.1` via a workspace-level override, rather than bumping `@gravity-ui/markdown-editor`.** Investigation during implementation found every recent `@gravity-ui/markdown-editor` release (14.12.0 through the current 15.47.0) exact-pins `uuid@11.0.5`; there is no upstream release that carries a fixed `uuid` forward (`npm audit`'s own suggested "fix" is actually a downgrade to `14.11.2`, predating the bad pin, which is not a viable direction). Since the vulnerable range is `uuid <11.1.1` and `11.1.1` is a same-major patch release, overriding `uuid` directly fixes the advisory with no editor version change and no breaking-change risk — safer than the originally planned major bump.
- **Remove the direct `markdown-it` dependency only if unused after the Diplodoc bump** — check actual imports first; if something in `core/frontend` (or a plugin frontend) imports it directly rather than only via Diplodoc, keep it and upgrade it in place instead.
- **Fix the test, not the UI, for `LoginPage.test.tsx`.** Read `LoginPage.tsx:190` and `:214`: the plain `Sign in` label for a single-provider form and the `Sign in with {provider}` label for multi-provider forms are both present and intentional-looking (distinct code paths for distinct scenarios), so the test regressed against an intentional UI simplification, not the other way around. Update the assertion to `Sign in` for the single local-credential-provider scenario it exercises.
- **CI wiring is explicitly out of scope here**, left to `harden-ci-and-supply-chain`, so this change's diff stays reviewable as "the dependency tree and one test are fixed," not entangled with pipeline-sequencing decisions that depend on other changes' state.

## Risks / Trade-offs

- **`linkify-it`/`svgo` overrides run an unsupported combination relative to what `@diplodoc/transform` declares** → mitigate by visually/snapshot-testing entity documentation and Flow documentation rendering before and after the override, not just checking `npm audit` output; document the override explicitly in the PR, and revisit once upstream `@diplodoc/transform` ships a real fix.
- **`markdown-it` itself stays un-upgraded, leaving 2 moderate ReDoS advisories open** → accepted risk (see Decisions); revisit if `@diplodoc/transform`/`@diplodoc/tabs-extension` ever drop their CJS deep-imports into `markdown-it/lib/*`, which would unblock a markdown-it bump.
- **`uuid` override could mismatch what `@gravity-ui/markdown-editor`'s bundled code expects** (an exact pin usually means the author tested against that exact version) → mitigate with manual smoke-testing of create/edit forms that use the Markdown editor (per `markdown-entity-documentation`) before merging, same as originally planned for the (now-avoided) major bump.
- **Hostile-input regression tests only cover what we think to test** → keep the test list explicit and tied to the specific advisories fixed here (ReDoS payload shapes, SVG script-injection payloads from the bypass advisories, deeply-nested/aliased YAML), not a vague "fuzz it" goal.
