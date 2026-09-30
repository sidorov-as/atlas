# Contributing

## Dev setup

Follow [Getting Started](../getting-started/index.md) for the Docker-based development setup. To work on the
backend or frontend directly on the host:

- `core/backend/README.md`: `uv sync`, host Django server, `pytest`, and the migration
  safety linter.
- `core/frontend/README.md`: `npm ci`, the Vite dev server, lint, tests, and build.

Run each component's lint, test, and build commands before submitting a change to it. New
migrations from Core and plugins are checked for destructive operations before they can land;
see [Operations](../deployment/operations.md) for how to mark a reviewed, genuinely safe one.

## How a change gets made

Nontrivial changes start with a proposal, so that the approach is agreed before the code is
written:

1. Open an issue that describes what is changing and why. If the change requires a design
   decision, record the alternatives and the approach you propose to take.
2. Wait for agreement from a maintainer, then implement the change in a pull request that links
   the issue. Split a large change into steps that can each be reviewed and merged on their own.
3. Update the documentation and tests in the same pull request, and run the validation for every
   component you touched.

Small, obvious fixes (typos, documentation, small bug fixes) don't need a proposal: open a
pull request directly.

!!! note "Looking for architecture decision records?"
    Atlas has no separate ADR log. The issue and pull request discussion records the alternatives
    and rationale for a decision, and the documentation describes the current, agreed behavior.

## Licensing

By contributing, you agree that your contributions will be licensed under the same license as
the rest of the repository (see `LICENSE`).
