// C4 frontend plugin — the C4 Diagram and System Architecture
// detail tabs, the diagram viewer components, viewer-preference storage, and the
// System Map page, moved out of the in-tree "core" plugin module
// (`frontend/src/plugins/core/`) into this independent, optional package boundary,
// matching `@atlas/plugin-standard-catalog` and `@atlas/plugin-apis`.
//
// The System Landscape diagram used to ship as a `homeWidget` contribution
// (rendered unconditionally on Home); it's now its own "System Map" nav
// destination (`route` + `navItem` in `./navItems`), moved off Home
import { defineFrontendPlugin } from '@atlas/plugin-api'
import { c4EntityDetailTabs } from './entityDetailTabs'
import { c4NavItems, c4Routes } from './navItems'

export const c4Plugin = defineFrontendPlugin({
  id: 'atlas.c4',
  contributions: [...c4EntityDetailTabs, ...c4Routes, ...c4NavItems],
})
