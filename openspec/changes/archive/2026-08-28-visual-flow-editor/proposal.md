## Why

Editing a Flow's steps as JSON is precise but cumbersome for authors who need to compose a process, connect branches, and attach catalog entities. The edit page already visualizes the tree and has a catalog lookup pattern, so a synchronized visual mode can make authoring substantially easier while retaining JSON for advanced edits and backward compatibility.

## What Changes

- Add a visual Flow-step editor that lets users create, edit, remove, reorder, and connect steps as a divergence-only tree.
- Add a mode switch between the Visual editor and the existing JSON editor; both modes operate on the same in-memory `steps` data and preserve all supported step fields.
- Provide a searchable, type-labelled catalog lookup for a step's optional `entity_ref`.
- Surface structural validation in the visual editor before save, including duplicate IDs, unknown targets, and prohibited branch reconvergence.
- Retain the JSON editor, its schema validation, the live graph preview, and the existing save API contract.

## Capabilities

### New Capabilities

- `visual-flow-editor`: Interactive visual authoring of Flow step trees, including catalog reference selection and synchronized JSON mode.

### Modified Capabilities

- `flow-management`: The Flow edit-page requirement gains a visual editing mode in addition to the existing JSON editor.

## Impact

- Frontend: `FlowFormPage`, a new reusable visual editor component, the existing `FlowGraph`, and catalog-reference selection helpers.
- Tests: new component/page tests for mode switching, mutations, validation, and reference lookup behavior.
- No backend model, endpoint, migration, or Flow `steps` JSON contract change is expected.
