## Why

Nearly every destructive or state-changing action in the catalog UI — Remove, Purge, Delete relationship, Delete flow, Unlink — currently gates on the browser's native `window.confirm()`. It's unstyled, blocks the render thread, can't be customized per-action, and gives no visual cue that "Purge" is permanent while "Remove" is revivable or "Unlink" isn't destructive at all. Since `@gravity-ui/uikit`'s `Dialog` (already used elsewhere in the app for `LinkServiceDialog`, `FlowTransitionModal`, `FlowStepModal`) ships a `Dialog.Footer` `preset` prop (`default` / `danger`) built for exactly this, replacing the native dialog is low-effort and closes a real visual/UX gap.

## What Changes

- Add a `useConfirm()` hook returning `confirm({ title, message, preset }): Promise<boolean>`, paired with a presentational `<ConfirmDialog>` built on `@gravity-ui/uikit`'s `Dialog`. State is local to the component that calls the hook (matches the existing local-dialog convention), not a global portal singleton.
- Replace all 8 `window.confirm()` call sites with the hook, preserving each site's existing confirmation copy and the async/loading/error-handling logic that already wraps the confirm gate:
  - `core/frontend/src/components/EntityListPage.tsx` — Remove (`default` preset)
  - `core/frontend/src/components/EntityDetailShell.tsx` — Remove (`default`) and Purge (`danger`)
  - `core/frontend/src/components/RelationsTab.tsx` — Delete relationship (`danger`)
  - `plugins/apis/frontend/src/components/OperationLinkedServicesTab.tsx` — Unlink (`default`)
  - `plugins/apis/frontend/src/components/EndpointLinkedServicesTab.tsx` — Unlink (`default`)
  - `plugins/flows/frontend/src/pages/FlowsListPage.tsx` — Delete (`danger`)
  - `plugins/flows/frontend/src/pages/FlowDetailPage.tsx` — Delete (`danger`)
- `EntityListPage` and `EntityDetailShell` are shared generic components reused by the Components, Systems, Teams, Resources, APIs, Endpoints, and Operations list/detail pages, and `RelationsTab` is shared across the API/System/Component/Resource detail tabs — so these edits cover nearly the entire catalog in a handful of file changes.

## Capabilities

### New Capabilities
- `confirm-dialog`: a reusable, severity-differentiated confirmation dialog (hook + component) for gating destructive or state-changing actions across the catalog frontend, replacing native browser `confirm()`.

### Modified Capabilities
None — existing specs (`catalog-web-ui`, `flows-plugin`, `endpoint-service-dependencies`, `operation-service-dependencies`, `architecture-relationships`) already require a confirmation gate before these actions but don't specify its presentation mechanism; this change only changes that presentation, which is new behavior captured entirely by the new `confirm-dialog` capability.

## Impact

- Affected code: `core/frontend/src/components/{EntityListPage,EntityDetailShell,RelationsTab}.tsx`, `core/frontend/src/lib/useConfirm.ts` (new, alongside `useAsync.ts`), `core/frontend/src/components/ConfirmDialog.tsx` (new), `plugins/apis/frontend/src/components/{OperationLinkedServicesTab,EndpointLinkedServicesTab}.tsx`, `plugins/flows/frontend/src/pages/{FlowsListPage,FlowDetailPage}.tsx`.
- Dependencies: none new — `@gravity-ui/uikit` is already a dependency and already provides `Dialog`/`Dialog.Footer` with the needed `preset` prop.
- No backend, API, or database changes; no changes to permission gating or the underlying Remove/Purge/Delete/Unlink semantics.
