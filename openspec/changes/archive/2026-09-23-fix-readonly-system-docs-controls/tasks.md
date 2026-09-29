## 1. Gate System Docs authoring

- [x] 1.1 Read the current session in `SystemDocsTab` and derive one document-link authoring predicate that requires both a manually managed System and a non-read-only session.
- [x] 1.2 Apply the authoring predicate to the Add action, document-link edit/remove row actions, and add/edit dialog while leaving search, pagination, open, and copy controls available.

## 2. Add regression coverage

- [x] 2.1 Extend the System Docs component test setup with controllable writable and read-only session states without changing the existing writable test expectations.
- [x] 2.2 Add a read-only regression test that verifies document links and non-mutating actions remain available while Add, edit/remove row actions, and the authoring dialog are absent.
- [x] 2.3 Verify that a session refresh to read-only removes an already-open authoring dialog and prevents continued writable interaction.

## 3. Validate the change

- [x] 3.1 Run the focused standard-catalog System detail-tab frontend tests.
- [x] 3.2 Run the applicable frontend static checks for the modified component and test files.
