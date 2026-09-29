## Context

`EndpointOverviewTab.tsx` was reworked interactively this session (not as a tracked change) to fix a cluster of layout complaints: `Documentation`'s title was trapped inside its own card padding, misaligned against the (unboxed) graph header; the summary/graph grid ran at `2fr:1fr` with a `360px` floor on the graph track; the `Details` card was a single flat column of ~9 fields with dead space beside the graph; and a redundant service list sat beneath the graph, duplicating the dedicated Linked Services tab. The fixes landed were: title-outside-box for card headers, a `3fr:2fr` grid with no floor, a `flex: 1` + `align-content: space-between` trick so `Details`' card stretches to match the graph's height, a `fillHeight` prop threaded through `CompactDependencyGraph`/`EndpointConsumersGraph` so the graph itself can grow past its `480px` default, and deleting the redundant list in favor of a "View all N services" link next to the graph header.

`OperationOverviewTab.tsx` was built from the same original template (`restructure-dependency-graph-layout`) and still has every one of those problems today, confirmed by measuring the live page: grid columns at `1045.33px : 522.665px` (exactly 2:1, the pre-fix ratio), a 16.5px offset between the `Documentation` title and the graph's title (the card-padding trap), a 203px gap between `Details`' actual bottom (906px) and the graph's fixed-height bottom (703px), no border around `Details` at all, and a full "Linked services" section duplicating the Linked Services tab. Since Endpoint's fixes were never captured as a tracked change, they had no mechanism to propagate to Operation's parallel file.

Operation's content shape isn't identical to Endpoint's, though: Endpoint has `Documentation` + `Details` (Details alone, ~9 fields, hence its internal 2-column grid); Operation has `Documentation` + `Channel` (~5 fields) + a conditionally-rendered `Message` section + `Details` (~4 fields). A straight copy of Endpoint's fix doesn't fit Operation's shape without adaptation — that adaptation is this design's subject.

## Goals / Non-Goals

**Goals:**
- Visual parity with `EndpointOverviewTab`'s current (already-shipped) layout: title-outside-box cards, `3fr:2fr` grid, graph height matching the adjacent card(s)' bottom edge, no Overview-level Linked Services duplication.
- Adapt that pattern to Operation's actual content shape (`Channel` + `Message` + `Details`) rather than forcing a byte-for-byte copy that doesn't fit.

**Non-Goals:**
- Extracting a shared layout component/CSS between `EndpointOverviewTab` and `OperationOverviewTab` — considered, declined (Decision 3).
- Touching `EndpointOverviewTab.tsx`/`.css`/`EndpointConsumersGraph.tsx` — already correct.
- Any change to `CompactDependencyGraph`'s public API — `fillHeight` already exists.
- Reconsidering what fields `Channel`/`Details`/`Message` show — only their placement changes.
- New spec requirements — this is presentation-only (see proposal.md's Capabilities section).

## Decisions

### 1. `Channel` and `Details` become a side-by-side row, not two independent full-width cards
**Decision:** Wrap both in a 2-column CSS grid (`.operation-channel-details-row { display: grid; grid-template-columns: 1fr 1fr; gap: 24px }`), each card keeping its own single-column label/value stack internally (Channel: up to 5 rows; Details: up to 4 rows) — not Endpoint's approach of a 2-column grid *inside* one card.

**Why:** Endpoint's `Details` needed an internal 2-column grid because it alone held ~9 fields. Operation splits similar content across two smaller sections; pairing them side by side uses the available width without forcing either into a sparse 2×2 internal grid, and keeps Channel (transport-level: address/protocol/direction) visually distinct from Details (catalog metadata: owner/system/tags) rather than merging their fields into one undifferentiated list.

**Alternative considered:** Merge Channel and Details into one combined card/list. Rejected — the two are conceptually different, and collapsing them loses that distinction for no layout benefit the row doesn't already provide.

### 2. `Message` moves to after the Channel/Details row, not before it
**Decision:** Reorder the left column to `Documentation → Channel/Details row → Message` (was `Documentation → Channel → Message → Details`).

**Why:** The height-matching trick (`flex: 1` + `align-content: space-between`, mirroring Endpoint's `Details`) needs a stable, unconditionally-present last element to flex-grow against the graph's height. `Message` only renders when `operation.messages.length > 0`; if it stayed last, the flex-grow target would need to switch between the row and `Message` depending on whether messages exist. Making the row always-last avoids that conditional-target branching entirely — a purely cosmetic property shouldn't need runtime logic to decide what it applies to.

**Alternative considered:** Keep `Message` between `Channel` and `Details` (splitting the row), or dynamically pick whichever section renders last as the flex target. Rejected both — the former defeats pairing Channel+Details adjacently; the latter adds real complexity for zero user-visible benefit.

### 3. Duplicate the fix into `OperationOverviewTab.tsx`/`.css` rather than extracting a shared layout component
**Decision:** Apply the same CSS ratio, flex/`align-content` trick, and graph-header pattern directly in Operation's own files, matching Endpoint's implementation by hand.

**Why:** `restructure-dependency-graph-layout`'s design.md already weighed this exact question for these same two files: *"Two call sites both need their own grid restructuring — not shared, since their non-graph content... differs enough that a shared layout wrapper would need as many escape hatches as it saves"* — and explicitly accepted the duplication. Decisions 1 and 2 above (the row, the reorder) reinforce that call: Operation's content shape now diverges from Endpoint's more, not less, so a shared wrapper would need to accommodate both shapes — more complexity than two independently-editable files.

**Risk this reintroduces:** the exact drift this change fixes could recur if a future Endpoint-side layout tweak isn't manually mirrored to Operation, same as happened this time. **Mitigation:** cross-referencing code comments on both files (task 5.1) — not a structural guard, but a nudge for the next editor. No stronger mitigation is in scope; it's the accepted cost of choosing duplication over extraction.

### 4. Graph header gains a "View all N services" link, replacing the removed bottom section
**Decision:** `OperationOverviewTab`'s "Publishers & subscribers" header row gets the same `justify-content: space-between` + conditional `Link` treatment `EndpointOverviewTab` already has, using the already-available `linkedServicesTotal`/`onViewLinkedServices` props (currently passed in only for the section being removed).

**Why:** Preserves the "jump to the full Linked Services tab" affordance the removed section provided, without duplicating the list itself — identical resolution to Endpoint's version of the same redundancy.

## Risks / Trade-offs

- **[Risk]** Manual duplication can drift again — this is the second time these two files have needed the same fix applied twice. → **Mitigation:** cross-reference comments (Decision 3); no stronger structural guard, by design (Option A was chosen explicitly over extraction).
- **[Risk]** Reordering `Message` after the Channel/Details row is a visible content-order change. → **Mitigation:** `Message` is supplementary payload detail, not primary identifying information (`Documentation`/`Channel` already establish what the operation does and how) — low risk of user confusion, and no data or functionality changes, only position.
- **[Risk]** `OperationOverviewTab.test.tsx` may assert DOM order or section structure that this reorder breaks. → **Mitigation:** covered explicitly in tasks (6.1) before considering this change done.

## Open Questions

None outstanding — the three open questions this change carried (Channel/Details row vs. Endpoint-style single-card grid, duplicate vs. extract, Message ordering) were resolved during exploration and are captured as Decisions 1–3 above.
