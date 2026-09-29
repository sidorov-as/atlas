## MODIFIED Requirements

### Requirement: Flow diagram layout direction and manual node positioning
A Flow SHALL carry a persisted `autolayout_enabled` boolean (default `true`) and a persisted `layout_direction` (`LAYOUT_LEFT_RIGHT` or `LAYOUT_TOP_DOWN`; default `LAYOUT_LEFT_RIGHT`). Each step MAY carry a `position` (`{x, y}`). Wherever the diagram is rendered — the read-only detail page or the edit page's canvas — a step SHALL render at its current `position`, with enough spacing between sibling nodes in the same layer that adjacent node borders do not touch.

While `autolayout_enabled` is `true`: any change to a Flow's `steps` — adding, removing, or editing a step, including a drag — SHALL trigger the automatic layout pass to recompute every step's `position` using `layout_direction`, and the recomputed values SHALL be persisted. A step's `position` therefore always reflects the most recent automatic layout computation for the Flow's current `steps` and `layout_direction`; no other value (e.g. a value set mid-drag, before the next recompute) persists across a subsequent `steps` change.

While `autolayout_enabled` is `false`: a step's `position` SHALL change only when an author drags it, when a new step is placed on being added (without invoking the automatic layout pass), or when the manual layout control described below is activated. No other `steps` change recomputes any step's `position`.

The edit page SHALL provide a manual-mode-only layout control that recomputes and overwrites every visible step's `position` once, using `layout_direction`, without changing `autolayout_enabled`. This control SHALL NOT be available while `autolayout_enabled` is `true`.

#### Scenario: While autolayout is on, every steps change recomputes and persists all positions
- **WHEN** `autolayout_enabled` is `true` and a Flow's `steps` are changed — a step is added, removed, or edited
- **THEN** every step's `position` is recomputed by the automatic layout pass using `layout_direction` and persisted, and the diagram re-renders accordingly

#### Scenario: While autolayout is on, a drag has no lasting effect
- **WHEN** `autolayout_enabled` is `true` and an author drags a node to a new location on the edit page's canvas
- **THEN** that drag is itself a `steps` change, so the automatic layout pass recomputes every step's `position` (including the dragged one) again, and the dragged node does not remain at the manually-dropped location

#### Scenario: While autolayout is off, dragging a node persists exactly that position
- **WHEN** `autolayout_enabled` is `false` and an author drags a node to a new location on the edit page's canvas
- **THEN** that step's `position` is updated to the new coordinates, and no other step's `position` changes

#### Scenario: While autolayout is off, a newly added step is placed without invoking automatic layout
- **WHEN** `autolayout_enabled` is `false` and a new step is added to the Flow
- **THEN** the new step is given a `position` that does not overlap any existing step, without recomputing any other step's `position`

#### Scenario: The manual layout control recomputes every position, once, without enabling autolayout
- **WHEN** `autolayout_enabled` is `false` and an author activates the manual layout control
- **THEN** every visible step's `position` is recomputed according to `layout_direction` and persisted, the canvas re-renders accordingly, and `autolayout_enabled` remains `false`

#### Scenario: The manual layout control is unavailable while autolayout is on
- **WHEN** `autolayout_enabled` is `true`
- **THEN** the edit page does not offer the manual layout control, since every `steps` change already keeps positions fully recomputed

#### Scenario: layout_direction is shared across viewers
- **WHEN** a Flow's `layout_direction` is `LAYOUT_TOP_DOWN` and two different users open its diagram
- **THEN** both render the diagram top-down, regardless of either user's own browser or session state
