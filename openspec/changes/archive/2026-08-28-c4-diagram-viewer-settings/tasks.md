## 1. Diagram rendering contract

- [x] 1.1 Define a typed diagram-rendering settings object, defaults, allowed
  layouts, and option-to-PlantUML payload mapping in the catalog C4 module.
- [x] 1.2 Update C4 payload builders so title, legend, layout, stereotypes,
  person sprites, and the selected-component label respect the rendering
  settings while retaining semantic role tags.
- [x] 1.3 Extend the diagram query schema and both diagram controllers to
  validate optional rendering settings and pass them to every supported view.
- [x] 1.4 Add backend tests for legacy defaults, valid non-default settings,
  hidden selected label retaining its tag, and invalid query values.

## 2. Viewer preferences and controls

- [x] 2.1 Create a versioned, validated localStorage preference module scoped
  by C4 diagram view, with legacy-equivalent defaults and invalid-value
  fallback.
- [x] 2.2 Extend diagram URL helpers and `DiagramTab` so active preferences
  are supplied to displayed SVG/PNG and download URLs.
- [x] 2.3 Add a lower-left Gravity UI Gear settings popup with a layout choice
  and independent display toggles; persist changes and reload the image.
- [x] 2.4 Add a `ResizeObserver`-based fit strategy that re-fits on meaningful
  viewport size changes without resetting zoom on unrelated renders.

## 3. Verification

- [x] 3.1 Add frontend tests for settings visibility, persisted preference URL
  mapping, download propagation, invalid storage fallback, and viewport resize
  fitting.
- [2] 3.2 Run focused backend and frontend test suites, lint/type checks, and
  manually verify each layout and display toggle in a visible diagram tab.
