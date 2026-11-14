## Why

Atlas already follows the operating system's light/dark preference through Gravity UI's `system` theme, but users cannot choose a theme themselves, and several surfaces ignore dark mode: C4 diagrams are rendered server-side with a fixed light palette on a forced white background, flow and ER exports hard-code a white background, and the OpenAPI and AsyncAPI documentation viewers have no dark styling. Teams that work in dark mode get a UI that is half dark and half bright white.

## What Changes

- Add a user-selectable theme mode (light, dark, system) with a switcher in the navigation shell footer. The choice is stored only in the browser (`localStorage`); the default stays system. The stored theme is applied before the application renders so a reload does not flash the wrong theme.
- Expose the current theme to the frontend and to plugins through a shared theme context, so plugin components can follow it.
- C4 diagram endpoints accept an optional `theme` parameter (`light` or `dark`). Absent, it is `light`, so MCP and any other existing consumer get unchanged output. A dark rendering uses its own palette for element tags, relationship tags, boundaries, legend, title, and diagram background while keeping role and interaction distinctions legible.
- The C4 viewer requests diagrams in the active theme and no longer forces a white backdrop. Switching theme reloads the displayed diagram.
- Diagram downloads (C4 SVG/PNG, flow export, ER export) are produced in the active theme. Non-transparent flow and ER exports use the active theme's page background instead of white; transparent export is unchanged.
- Flow and ER canvases, and the OpenAPI and AsyncAPI documentation viewers, follow the active theme.
- Out of scope: the documentation site, MCP tool behavior, per-user server-side theme storage, custom color themes beyond light and dark.

## Capabilities

### New Capabilities
- `ui-theme`: Theme mode selection (light, dark, system), its browser-only persistence, the footer switcher, flash-free initial application, a shared theme context for plugins, and theme-following behavior of the code editor, flow and ER canvases and exports, and API documentation viewers.

### Modified Capabilities
- `catalog-c4-diagrams`: Diagram endpoints accept an optional `theme` option defaulting to `light`; dark rendering uses a dedicated palette for elements, relationships, boundaries, legend, title, and background.
- `c4-custom-view-diagram`: Custom view preview and saved-view diagram endpoints accept the same `theme` option, and the dark rendering keeps the existing semantic styling.
- `c4-diagram-viewer-preferences`: The viewer's image and download requests carry the active UI theme, and a theme change reloads the displayed diagram.

## Impact

- Backend: `plugins/c4/backend/atlas_plugin_c4` (`c4.py` rendering settings and palettes, `api/schemas.py`, `api/views.py`, `custom_view.py`), plus its tests.
- Frontend core: `App.tsx`, `AppShell.tsx`, `index.html`, a new theme context under `lib/`, `package.json` exports.
- Frontend plugins: `c4` (diagram URL builders, `DiagramTab`, view pages), `flows` and `database-schema` (canvas color mode and export background), `apis` (Redoc and AsyncAPI viewers).
- API: one new optional query parameter on C4 diagram endpoints; backward compatible.
- Dependencies: none expected; relies on existing Gravity UI theming and `@xyflow/react` color mode.
