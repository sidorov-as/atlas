## 1. Structured Flow editing foundations

- [x] 1.1 Extract Flow-step parsing, serialization, ID generation, and strict-tree client validation into testable frontend utilities while preserving the backend JSON contract.
- [x] 1.2 Add focused unit tests for valid linear/branched steps and for duplicate IDs, unknown targets, cycles, and reconverging branches.
- [x] 1.3 Adapt Flow form state so JSON and Visual modes use one canonical steps representation and retain invalid JSON text and diagnostics until it is corrected.

## 2. Visual Flow editor

- [x] 2.1 Build a Gravity UI visual step-card editor that exposes id, title, summary, add/remove/reorder, and focus management.
- [x] 2.2 Add single-transition and branching-transition controls that update `next_step` and `next_steps`, including labels and client-side structural feedback.
- [x] 2.3 Integrate the existing grouped, searchable catalog target lookup as the optional step entity-reference control, including clear behavior.
- [x] 2.4 Add component tests for step mutations, transition constraints, and canonical `entity_ref` selection.

## 3. Flow form integration

- [x] 3.1 Add the compact Steps settings control for switching Visual and JSON modes, preserving valid edits in both directions and explaining why invalid JSON cannot enter Visual mode.
- [x] 3.2 Keep Add Step, editor collapse/expand, graph-node focus, live preview, and save behavior working with the active mode.
- [x] 3.3 Add Flow form tests covering mode synchronization, invalid JSON retention, visual edits reflected in the preview payload, and graph-to-card focus.

## 4. Verification

- [x] 4.1 Run frontend lint, typecheck, and the relevant Vitest suite; fix all reported failures.
- [x] 4.2 Manually verify the booking Flow example in both modes, including its availability branches and entity lookup selections.
- [x] 4.3 Validate the OpenSpec change with `openspec validate visual-flow-editor --strict`.
