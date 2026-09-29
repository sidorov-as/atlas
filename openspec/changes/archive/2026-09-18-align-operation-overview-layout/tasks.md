## 1. Card title placement

- [x] 1.1 Move `Documentation`'s title in `OperationOverviewTab.tsx` outside its bordered box (title above, box wraps only `MarkdownDescription`) — mirrors `EndpointOverviewTab.tsx`'s existing `Documentation` section.
- [x] 1.2 Move `Channel`'s title outside its bordered box the same way.

## 2. Channel/Details row

- [x] 2.1 Add `.operation-channel-details-row` to `OperationOverviewTab.css` (2-column CSS grid, `1fr 1fr`, gap matching this file's existing conventions).
- [x] 2.2 Wrap the `Channel` and `Details` sections in that row container; give `Details` a bordered card (`CARD_STYLE`) — it currently has none.
- [x] 2.3 Move the `Details` section to sit immediately after `Channel` (before `Message`), reordering the left column to Documentation → Channel/Details row → Message.
- [x] 2.4 Make the row's parent flex item `flex: 1` / `minHeight: 0` (mirroring `EndpointOverviewTab`'s `Details` section) so the row stretches to fill the left column's available height.
- [x] 2.5 Give each of `Channel`'s and `Details`' inner content containers `display: flex; flex-direction: column; flex: 1` plus `align-content: space-between` (or the flex-column equivalent, `justify-content: space-between`) so each card's own label/value stack fills its card's stretched height independently — matching `.endpoint-details-grid`'s treatment.

## 3. Grid ratio and graph height

- [x] 3.1 Update `.operation-overview-grid` in `OperationOverviewTab.css` from `minmax(0, 2fr) minmax(360px, 1fr)` to `minmax(0, 3fr) minmax(0, 2fr)`, matching `.endpoint-overview-grid`.
- [x] 3.2 Pass `fillHeight` from `OperationConsumersGraph.tsx` into its `CompactDependencyGraph` call (the prop already exists on `CompactDependencyGraph`, added for `EndpointConsumersGraph`).
- [x] 3.3 Wrap the graph section's right column in `OperationOverviewTab.tsx` the same way as Endpoint's: flex column, header row, `flex: 1` / `minHeight: 0` wrapper div around `OperationConsumersGraph`.

## 4. Graph header link, remove duplicate Linked Services section

- [x] 4.1 Add a "View all N services" `Link` next to the "Publishers & subscribers" header, conditional on `linkedServicesTotal > 0`, using the existing `onViewLinkedServices` callback — mirrors `EndpointOverviewTab`'s header row.
- [x] 4.2 Remove the full-width "Linked services" section at the bottom of `OperationOverviewTab`'s Overview (its list/empty-state block and own header) — now redundant with the dedicated Linked Services tab and the new header link.
- [x] 4.3 Remove the now-unused `linkedServices` prop from `OperationOverviewTab`'s props and its call site in `OperationDetailPage.tsx` (the capped-to-5 preview list, e.g. `.slice(0, 5)`) — confirm nothing else reads it first. Keep `linkedServicesTotal` — it's still used by 4.1.

## 5. Cross-reference comments

- [x] 5.1 Add a short comment in `EndpointOverviewTab.tsx`/`.css` and `OperationOverviewTab.tsx`/`.css` pointing at each other (e.g. "layout intentionally duplicated, not shared — see design.md of align-operation-overview-layout; mirror layout-only changes in the other file"), per design.md Decision 3's mitigation.

## 6. Verification

- [x] 6.1 Update `OperationOverviewTab.test.tsx` for the new section grouping/order (Channel+Details row, Message after it, no bottom Linked Services section, header link presence/absence based on `linkedServicesTotal`).
- [x] 6.2 Run the `plugins/apis/frontend` test suite and confirm all updated tests pass.
- [x] 6.3 Manually verify the Operation Overview tab at a wide viewport: `Documentation`/graph header baselines aligned; `Channel`/`Details` row bottom-aligned with each other and with the graph; for an operation with 0, a few, and >12 linked participants, and with/without messages. (Verified with 0 and 2 linked-services operations, with and without messages, against seed data — the demo dataset has no operation with >12 participants to exercise the overflow cap; that capping logic itself is unchanged by this layout-only change.)
- [x] 6.4 Manually verify the ~1200px collapse-to-single-column breakpoint still behaves correctly with the new row structure. (Verified at 1000px: grid collapses to a single column, Channel/Details row stays side-by-side. The row's own 560px breakpoint reuses `.endpoint-details-grid`'s already-shipped pattern verbatim.)
