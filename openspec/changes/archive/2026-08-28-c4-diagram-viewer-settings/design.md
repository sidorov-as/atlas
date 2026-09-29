## Context

Atlas renders C4 diagrams server-side through `c4-diagrams` and PlantUML, then
displays the resulting image in a shared React viewer. The current backend
always emits a top-down layout, title, and legend, while the component builder
adds `(selected)` to the selected component label. The viewer fits only after
image load and browser-window resize, so a tab becoming visible can leave the
image at a stale, undersized scale.

The preferences are presentation choices for an individual viewer, not catalog
metadata. They must not require a database migration or change an entity for
other users.

## Goals / Non-Goals

**Goals:**

- Let a viewer choose one supported layout and independently toggle title,
  legend, selected-label text, person sprites, and stereotypes.
- Restore a user's choices for each C4 view from browser storage.
- Render the same choices in the viewed SVG/PNG and downloaded files.
- Automatically re-fit a loaded diagram when its viewport changes dimensions.
- Preserve today's rendering when no settings query parameters are present.

**Non-Goals:**

- Persisting settings in the Atlas database, sharing them with other users, or
  adding them to catalog manifests.
- Arbitrary PlantUML input, custom colours, tag styling, or manual node
  positioning.
- Changing the selected element's semantic highlight when its text suffix is
  hidden.

## Decisions

### Versioned local preferences, scoped by diagram view

The frontend will store a compact, versioned preference object in `localStorage`
under one application-owned key. Values are keyed by diagram view (`context`,
`architecture`, `component`, and `landscape`), not by entity id. This permits a
choice that works well for Component Diagrams to follow the user across
components without unexpectedly changing Context Diagrams.

Malformed, unavailable, or old storage values fall back to defaults. Defaults
match the current output: top-down layout with title, legend, selected label,
person sprite, and stereotypes visible.

Alternative: put all state only in React component state. Rejected because it
loses a deliberate user choice between navigations. Alternative: store it on
the server. Rejected because these are personal display preferences and would
add account data, APIs, and migration work.

### A constrained settings contract travels in image URLs

The frontend maps the local preference object to explicit query parameters for
both normal image and download URLs. The backend query schema accepts only the
three renderer-supported layouts and boolean display options, then passes a
typed settings object into all C4 payload builders. Missing options use the
legacy default configuration.

The backend will apply: `layout`, optional `show_legend`, global
`hide_stereotype`, `hide_person_sprite`, optional title, and a selected-label
flag. It will continue to own all semantic styles and never accept raw
PlantUML or free-form tags.

Alternative: remove features from the already-loaded SVG in the browser.
Rejected because PlantUML layout and legend affect image dimensions and PNG
downloads must precisely match the viewed configuration.

### Gear settings popup uses existing Gravity UI primitives

The shared viewer renders an icon-only Gear button in its lower-left overlay
after a successful image load. A keyboard-accessible Gravity UI popup contains
a segmented layout control and checkbox-like display controls. Existing
zoom/fit/download controls remain in the upper-right overlay.

Changing a preference immediately replaces the image URL, resets pan/zoom
through the normal image-load fit path, persists the new value, and updates
the download URLs.

### ResizeObserver drives fitting on container changes

The viewer observes its viewport element with `ResizeObserver`. After an image
has intrinsic dimensions and the viewport receives a non-zero size, the
observer schedules `fitToViewport` in the next animation frame. It is cleaned
up on unmount. Window resize handling may be removed once covered by the
observer.

This addresses hidden-to-visible tabs and layout changes that do not emit a
window resize. User-initiated pan/zoom must not be overwritten by unrelated
renders; fitting occurs on image load and meaningful viewport-size changes.

## Risks / Trade-offs

- [A resize loop resets a user's manual zoom] → Observe dimensions only and
  schedule fitting only when width or height actually changes; do not couple
  it to general React state updates.
- [Old deep links could change appearance] → Omitted query parameters retain
  the established server defaults.
- [Many option combinations expand test work] → Test the typed option mapping,
  default payload, representative non-default payload, URL propagation, and
  resize behaviour rather than snapshotting every combination.
- [Stereotypes and person sprites are easily confused] → Present them as
  distinct controls and test that `hide_stereotype` and
  `hide_person_sprite` map independently.

## Migration Plan

1. Deploy backend support with absent parameters defaulting to the legacy
   rendering configuration.
2. Deploy the frontend settings UI and localStorage reader/writer.
3. Existing URLs, browser storage, and downloads continue to work without a
   migration; invalid storage is discarded in favour of defaults.
4. Roll back by removing the frontend control. URLs without settings still
   render identically; the backend can safely ignore or later remove the new
   optional query parameters.

## Open Questions

None. The initial scope intentionally offers only the three layouts exposed by
the installed renderer and the agreed display toggles.
