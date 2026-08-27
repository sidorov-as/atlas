# Contributing to Atlas

Thanks for your interest in contributing! This file is a quick entry point; the
full guide lives on the
[documentation site](https://sidorov-as.github.io/atlas/contributing/) and is the
source of truth if anything here goes out of date.

## Dev setup

Follow the [Getting Started guide](https://sidorov-as.github.io/atlas/getting-started/)
for the Docker-based development setup. To work on a single component directly on
the host instead:

- [`core/backend/README.md`](core/backend/README.md): Poetry install, host Django
  server, `pytest`, and the migration safety linter.
- [`core/frontend/README.md`](core/frontend/README.md): `npm ci`, the Vite dev
  server, lint, tests, and build.

Run each component's lint, test, and build commands before submitting a change to
it.

## How a change gets made

Atlas discusses nontrivial changes before they are implemented, rather than
jumping straight to a PR:

1. Open an issue describing what's changing and why, and the alternatives if
   there is a real design decision.
2. Implement the change in a pull request that links the issue, once a
   maintainer has agreed to the approach. Split a large change into steps that
   can each be reviewed on their own.
3. Update the documentation and tests in the same pull request.

Small, obvious fixes (typos, docs, small bug fixes) don't need a proposal: open a
PR directly. When in doubt, see the
[full contributing guide](https://sidorov-as.github.io/atlas/contributing/) for
more detail on this workflow.

## Reporting bugs and requesting features

Use the issue templates when opening a GitHub issue. For security
vulnerabilities, see [`SECURITY.md`](SECURITY.md) instead; please don't file a
public issue for those.

## Code of Conduct

This project follows the [Code of Conduct](CODE_OF_CONDUCT.md). By participating,
you're expected to uphold it.

## Licensing

By contributing, you agree that your contributions will be licensed under the same
license as the rest of the repository (see [`LICENSE`](LICENSE)).
