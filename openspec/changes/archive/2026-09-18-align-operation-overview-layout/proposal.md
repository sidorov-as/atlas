## Why

`OperationOverviewTab` still has the layout problems `EndpointOverviewTab` had before this session's ad hoc fixes: card titles trapped inside their own padding (misaligned against the graph's header baseline), a graph pinned to a fixed 480px height that stops well short of the summary content's actual bottom, a 2fr:1fr grid ratio where Endpoint now uses 3fr:2fr, a `Details` card with no border at all, and a full "Linked services" list duplicated in Overview despite a dedicated Linked Services tab already existing. Both tabs were built from the same template and are deliberately kept as separate, unshared implementations (`restructure-dependency-graph-layout`'s design.md already weighed and rejected sharing them), so Endpoint's fixes — made interactively, outside any tracked change — never propagated to Operation. Users comparing an Endpoint's and an Operation's Overview tab side by side see visibly inconsistent layouts as a result.

## What Changes

- `Documentation` and `Channel` card titles move outside their bordered boxes (title above, box wraps only the content) — matches `Details`' existing pattern and fixes the header-baseline mismatch against the graph's own header.
- `.operation-overview-grid` widens from `minmax(0, 2fr) minmax(360px, 1fr)` to `minmax(0, 3fr) minmax(0, 2fr)`, matching `.endpoint-overview-grid`.
- `Channel` and `Details` merge into one side-by-side row (each keeps its own bordered card); `Details` currently has no card at all and gains one. `Message` (rendered only when the operation has messages) moves to after this row, so the row — not a conditionally-rendered section — is always the last, stable element in the left column.
- The row's two cards flex to fill the row's stretched height, each distributing its own label/value rows with `align-content: space-between` — mirrors `Details`' existing treatment on the Endpoint page, so both cards' bottom edges land level with each other and with the graph.
- `OperationConsumersGraph` passes the already-existing `fillHeight` prop through to `CompactDependencyGraph`, so the graph grows past its 480px floor to match the row's height instead of stopping short of it.
- The full "Linked services" section at the bottom of Operation Overview is removed; a "View all N services" link is added next to the "Publishers & subscribers" graph header instead — mirrors Endpoint's Overview and removes the redundancy with the dedicated Linked Services tab (search/filter/sort already live there).

**Non-goals:** no shared layout component extraction between `EndpointOverviewTab` and `OperationOverviewTab` (considered and declined — see design.md); no changes to Endpoint's already-fixed files; no changes to what Channel/Details/Message fields show, only where they sit; no backend or API changes.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `operation-service-dependencies`: adds a requirement that the Overview tab surfaces linked Services only via the compact graph + a "View all" link to the Linked Services tab, not a duplicated list embedded in Overview. This is the one piece of "What Changes" above that's a genuine requirement, not pure CSS/placement — it prevents the removed section from quietly regressing back in later.
- `endpoint-service-dependencies`: adds the identical requirement, documentation-only — `EndpointOverviewTab` already complies (fixed interactively, before this requirement existed in writing); no code changes accompany this delta.

Everything else in "What Changes" (title placement, grid ratio, the Channel/Details row, graph `fillHeight`) is presentation/placement only — no other requirement in either capability specifies exact card layout or grouping, so nothing else here needs a delta. (Consistent with `restructure-dependency-graph-layout`, whose equivalent grid-ratio work needed no spec delta either — only its fullscreen-mode addition did.)

## Impact

- `plugins/apis/frontend/src/components/OperationOverviewTab.tsx` — title placement, new Channel/Details row, Message reorder, graph header "View all" link, removal of the bottom Linked Services section.
- `plugins/apis/frontend/src/components/OperationOverviewTab.css` — grid ratio, new row/stretch CSS.
- `plugins/apis/frontend/src/components/OperationConsumersGraph.tsx` — one line, pass `fillHeight`.
- `plugins/apis/frontend/src/pages/OperationDetailPage.tsx` — drop the now-unused `linkedServices` (capped-to-5 preview list) prop/computation once the section reading it is removed.
- `plugins/apis/frontend/src/components/OperationOverviewTab.test.tsx` — update for the new section grouping/order.
- No backend, migration, or shared-component API changes — `CompactDependencyGraph`'s `fillHeight` prop already exists (added earlier for `EndpointConsumersGraph`); `EndpointOverviewTab.tsx`/`.css`/`EndpointConsumersGraph.tsx` are not touched by this change.
