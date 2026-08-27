// Shared lookup item-row shape for FlowStepModal's catalog lookups: one item-row renderer and one loading-state
// treatment reused by both the entity_ref lookup and the
// query_ref/event_ref lookup, so both read as one consistent
// control despite keeping different fetch strategies underneath.
import type { ReactNode } from 'react'
import { Text } from '@gravity-ui/uikit'
import type { PopupPlacement } from '@gravity-ui/uikit'

/** Row height (px) reserved for a two-line lookup-result item — Gravity UI's `Select` otherwise sizes virtualized rows for its default single-line content. */
export const LOOKUP_OPTION_HEIGHT = 56

/** Two-line lookup-result content: an optional leading icon (already rendered, e.g. `<Icon data={...} size={16} />`, so this component stays agnostic to which icon set a given lookup draws from), primary text, and secondary text. Rendered via `renderOption` (not `Select`'s default `content` slot): the default slot wraps `content` in a `span.g-select-list__option-default-label` whose height is fixed to a single line regardless of `getOptionHeight`, which silently clips a second line. `renderOption` bypasses that wrapper entirely. */
export function LookupOptionRow({ icon, primary, secondary }: { icon?: ReactNode; primary: string; secondary: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 0', minHeight: '100%' }}>
      {icon}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 2, justifyContent: 'center', minWidth: 0 }}>
        <Text variant="body-2">{primary}</Text>
        <Text color="secondary" variant="caption-2">{secondary}</Text>
      </div>
    </div>
  )
}

/** `renderOption` for a lookup `Select` built from `LookupOptionRow` items — passes each option's already-built `content` through directly (see `LookupOptionRow`'s note). */
export function renderLookupOption(option: { content?: ReactNode }) {
  return <>{option.content}</>
}

/** Class applied to a lookup `Select`'s popup (paired with the `.flow-lookup-popup .g-select-list` rule in `core/frontend/src/index.css`) so its option list scrolls within a capped height instead of growing to fit every row. */
const LOOKUP_POPUP_CLASS_NAME = 'flow-lookup-popup'

/** Shared loading-state treatment: spread onto a `Select` alongside its `options`/`value`/`onUpdate` so a fetch-in-flight renders the same "keep the popup open with a loading row" visual — Gravity UI's `Select` only keeps its option list (and thus a `loading` sentinel row) mounted while `loading` is true or matches exist, otherwise it swaps to an empty-state — instead of each lookup wiring `loading`/`getOptionHeight`/`renderOption` separately and drifting out of sync.
 *
 * Also caps and pins the popup: Gravity UI's `Select` popup has no built-in limit on its
 * height relative to available viewport space, and the two-line `LookupOptionRow` rows
 * (56px) make a popup roughly twice as tall as the single-line rows it replaced for the
 * entity_ref field — tall enough, often, to not fit below the field, which made `flip`
 * reposition the (still-uncapped) popup above it, covering the whole dialog.
 * `popupClassName` bounds the option list's own scroll height via CSS instead of letting it
 * grow to fit every row, and `popupPlacement` keeps the popup below the field rather than
 * letting `flip` move it above — between the two, the popup never covers the rest of the
 * dialog. */
export function lookupSelectLoadingProps(loading: boolean) {
  return {
    loading,
    getOptionHeight: () => LOOKUP_OPTION_HEIGHT,
    renderOption: renderLookupOption,
    popupClassName: LOOKUP_POPUP_CLASS_NAME,
    popupPlacement: ['bottom-start', 'bottom-end'] as PopupPlacement,
  }
}
