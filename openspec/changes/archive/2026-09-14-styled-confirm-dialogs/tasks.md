## 1. Shared confirm dialog primitive

- [x] 1.1 Add `core/frontend/src/lib/useConfirm.ts` — a hook returning `{ confirm, dialogProps }`, where `confirm({ title, message, confirmText?, cancelText?, preset }): Promise<boolean>` resolves `true` on confirm and `false` on cancel/outside-click/Escape, and `dialogProps` is passed to `<ConfirmDialog>`.
- [x] 1.2 Add `core/frontend/src/components/ConfirmDialog.tsx` — a presentational component wrapping `@gravity-ui/uikit`'s `Dialog`/`Dialog.Header`/`Dialog.Body`/`Dialog.Footer`, taking `dialogProps` from `useConfirm` and rendering `Dialog.Footer` with `preset: 'default' | 'danger'`.
- [x] 1.3 Add a component/hook test covering: confirm resolves `true`, cancel resolves `false`, outside-click/Escape resolves `false`, and `danger`/`default` preset is forwarded to `Dialog.Footer`.

## 2. Core entity pages (covers Components, Systems, Teams, Resources, APIs, Endpoints, Operations)

- [x] 2.1 `core/frontend/src/components/EntityListPage.tsx`: replace `window.confirm(...)` in `handleRemove` with `useConfirm()` (`preset: 'default'`), preserving the existing message text; render `<ConfirmDialog {...dialogProps} />`.
- [x] 2.2 `core/frontend/src/components/EntityDetailShell.tsx`: replace `window.confirm(...)` in `handleRemove` with `useConfirm()` (`preset: 'default'`) and in `handlePurge` with a second `useConfirm()` (`preset: 'danger'`), preserving existing message text for each; render both `<ConfirmDialog>` elements.
- [x] 2.3 Update/extend existing tests for `EntityListPage` and `EntityDetailShell` that currently stub `window.confirm` to instead drive the rendered `ConfirmDialog`.

## 3. Relations tab (covers API/System/Component/Resource detail tabs)

- [x] 3.1 `core/frontend/src/components/RelationsTab.tsx`: replace `window.confirm(...)` in `deleteRelationship` with `useConfirm()` (`preset: 'danger'`), preserving existing message text; render `<ConfirmDialog>`.
- [x] 3.2 Update `RelationsTab.test.tsx` accordingly.

## 4. APIs plugin — linked services

- [x] 4.1 `plugins/apis/frontend/src/components/OperationLinkedServicesTab.tsx`: replace `window.confirm(...)` with `useConfirm()` (`preset: 'default'`), preserving existing message text.
- [x] 4.2 `plugins/apis/frontend/src/components/EndpointLinkedServicesTab.tsx`: replace `window.confirm(...)` with `useConfirm()` (`preset: 'default'`), preserving existing message text.

## 5. Flows plugin

- [x] 5.1 `plugins/flows/frontend/src/pages/FlowsListPage.tsx`: replace `window.confirm(...)` with `useConfirm()` (`preset: 'danger'`), preserving existing message text.
- [x] 5.2 `plugins/flows/frontend/src/pages/FlowDetailPage.tsx`: replace `window.confirm(...)` with `useConfirm()` (`preset: 'danger'`), preserving existing message text.

## 6. Verification

- [x] 6.1 Grep the frontend tree for `window.confirm` and confirm zero remaining call sites.
- [x] 6.2 Run the frontend test suite (core + apis + flows) and confirm it passes (412/413; the one failure — `TeamsListPage` maxWidth assertion — is pre-existing and unrelated, verified by reproducing it on a stash of this change).
- [x] 6.3 Manually exercised Remove live in the running app (Systems list): styled Gravity UI dialog opens with the exact original copy, `default`-styled Confirm button, no native `window.confirm()`, and Cancel left the entity unchanged. Browser automation tooling proved unreliable partway through (a stray click against the Flows "Delete" confirm dialog actually fired the delete, requiring a `seed_booking_demo` + `seed_flow_layout_tests` reseed to restore the dev DB — done, with user confirmation), so Purge/Delete relationship/Delete flow/Unlink were not each re-exercised live; they're covered instead by the automated tests added in 2.3/3.2/6.2's site-level suites, which render the real `ConfirmDialog` (not a mocked `window.confirm`) and assert exact copy, danger-vs-default `preset` styling, and that Cancel leaves state unchanged.
