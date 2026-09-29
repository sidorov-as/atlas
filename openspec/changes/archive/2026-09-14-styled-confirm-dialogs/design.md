## Context

Eight call sites across the catalog frontend gate a destructive or state-changing action on `window.confirm(message)`:

| Site | Action | Reversible? |
|---|---|---|
| `core/frontend/src/components/EntityListPage.tsx` | Remove | Yes (revivable) |
| `core/frontend/src/components/EntityDetailShell.tsx` | Remove | Yes (revivable) |
| `core/frontend/src/components/EntityDetailShell.tsx` | Purge | No |
| `core/frontend/src/components/RelationsTab.tsx` | Delete relationship | No |
| `plugins/apis/frontend/src/components/OperationLinkedServicesTab.tsx` | Unlink | N/A — not destructive |
| `plugins/apis/frontend/src/components/EndpointLinkedServicesTab.tsx` | Unlink | N/A — not destructive |
| `plugins/flows/frontend/src/pages/FlowsListPage.tsx` | Delete | No |
| `plugins/flows/frontend/src/pages/FlowDetailPage.tsx` | Delete | No |

`EntityListPage` and `EntityDetailShell` are generic components reused by the Components, Systems, Teams, Resources, APIs, Endpoints, and Operations pages; `RelationsTab` is reused by the API/System/Component/Resource detail tabs. So two file edits plus one shared-tab edit account for the bulk of the catalog's "almost every section" surface.

`@gravity-ui/uikit` is already a project dependency, and the codebase already has an established idiom for dialogs: state lives in the component that owns the action, and the dialog itself is a local, prop-driven element (`LinkServiceDialog`, `FlowTransitionModal`, `FlowStepModal` all follow `open`/`onClose` passed down from parent `useState`). There is no global modal manager or portal singleton anywhere in the app today.

## Goals / Non-Goals

**Goals:**
- Replace all 8 `window.confirm()` calls with a styled Gravity UI dialog, with zero change to each site's existing gate semantics, confirmation copy, or the async/loading/error handling that wraps it.
- Visually differentiate permanent/irreversible actions (Purge, Delete relationship, Delete flow) from revivable or non-destructive ones (Remove, Unlink), using `Dialog.Footer`'s built-in `preset` prop (`default` | `danger`) rather than hand-rolled button styling.
- Keep the dialog's state local to the calling component, consistent with every other dialog in the codebase.

**Non-Goals:**
- No global/portal-based confirm singleton (e.g., mounted once in `App.tsx` and called from anywhere without local state). That would be a new architectural pattern this codebase doesn't otherwise use, and isn't needed since every existing call site already owns a component with local state.
- No behavior changes to Remove/Purge/Delete/Unlink themselves (permissions, backend semantics, revivability) — this is purely a presentation-layer swap.
- No `success` preset usage — none of the 8 actions warrant it; only `default` and `danger` are used.
- No bulk/multi-select confirm flow — none of the 8 sites currently support bulk delete, so it's out of scope.

## Decisions

### Decision 1: `useConfirm()` hook + `<ConfirmDialog>` component, not per-site dialogs, not a global singleton

Each of three architectures was considered:
- **Per-site local `<Dialog>`** (copy the `LinkServiceDialog` pattern 8 times): zero new abstractions, but ~15 lines of near-identical `useState`/JSX duplicated 8 times, and severity/copy choices drift apart over time with no single place enforcing consistency.
- **Global imperative `confirm()`** mounted once in `App.tsx` via a portal: smallest per-call-site diff, but introduces the app's first global UI singleton, a pattern with no precedent here — bigger conceptual footprint than the problem warrants.
- **`useConfirm()` hook returning `confirm(options): Promise<boolean>`, paired with a `<ConfirmDialog>` presentational component** (chosen): each call site calls the hook once, renders the dialog element it returns once, and gates with `if (!(await confirm({...}))) return` — nearly identical shape to today's `if (!window.confirm(...)) return`. Severity/copy are still per-call parameters (not centralized/hardcoded), but the rendering and Promise-resolution plumbing is shared. State stays local to the component, matching every existing dialog in the app.

### Decision 2: `preset: 'danger' | 'default'` maps directly to reversibility, not to "is this a delete"

`Dialog.Footer` supports `preset: 'default' | 'success' | 'danger'` already, applying the right button `view` (e.g., `danger` → `outlined-danger`/red Apply button) with no need to hand-pick a `ButtonView`. The mapping is by consequence, not by verb:
- `danger`: Purge, Delete relationship, Delete flow — all permanently destroy data with no recovery path.
- `default`: Remove — soft-delete, revivable via the existing Revive action — and Unlink — removes a relation edge, not an entity; nothing is destroyed.

This means "Delete" and "Remove" are not synonyms for severity purposes even though both are removal-shaped verbs; the existing product semantics (`entity-removal-lifecycle` spec: Remove is revivable, Purge is not) are the source of truth, not the button label.

### Decision 3: Preserve exact confirmation copy and control flow at each site

The hook only replaces the confirmation *mechanism*. Each site keeps its existing message text (e.g. `Remove "${item.metadata.title}"? It can be revived later.`), and the code after the gate (`setIsRemoving(true)`, `try/finally`, error handling) is untouched — only `if (!window.confirm(msg)) return` becomes `if (!(await confirm({ title, message: msg, preset }))) return`. This keeps the change reviewable as a mechanical swap rather than a UX rewrite, and avoids re-opening copy decisions that are out of scope here.

### Decision 4: `useConfirm()` lives in `core/frontend/src/lib/` (next to `useAsync.ts`), `ConfirmDialog` in `core/frontend/src/components/`

Matches the existing split in this codebase: hooks in `lib/`, components (including other dialogs like `LinkServiceDialog`) in `components/` (or a plugin's local `components/`). `ConfirmDialog` is exported from core so plugin code (`plugins/apis/...`, `plugins/flows/...`) can import it the same way those plugins already import other core UI (e.g. `EntityListPage`, `EntityDetailShell`).

## Risks / Trade-offs

- **[Risk]** `window.confirm()` is synchronous and blocks the calling code inline; a Promise-based dialog introduces a real async gap (user could navigate away, or trigger the same action twice, while the dialog is open) → **Mitigation**: each site already wraps the action in a loading-state guard (`isRemoving`/`isPurging`/`submitting`) that disables the triggering control while in flight; `confirm()`'s async gap sits entirely before that guard engages, and the action buttons that open the dialog are unaffected by this change, so double-invocation risk doesn't increase relative to today.
- **[Risk]** Eight call sites means eight small edits instead of one; a mismatched `preset` or garbled copy in any one of them is a real (if low-severity) regression risk → **Mitigation**: table in Context above is the checklist; each site's existing message string is copied verbatim into the new call.
- **[Trade-off]** Keeping state local to each calling component (vs. a global singleton) means each of the 8 sites needs one extra `useConfirm()` line and one rendered `<ConfirmDialog>` element, instead of a bare function call — slightly more boilerplate per site, in exchange for staying consistent with the rest of the app's dialog architecture.

## Migration Plan

No data or API migration. Rollout is a straightforward code change: land the new `useConfirm`/`ConfirmDialog`, then swap the 8 call sites (can be done as one PR or incrementally site-by-site, since each site is independent and behaviorally equivalent before/after). No feature flag needed — this is a pure UI mechanism swap with identical gate semantics, safe to ship directly. Rollback is a plain revert.

## Open Questions

None — architecture, severity mapping, and copy-preservation were confirmed with the user before this design was written.
