"""Composer CLI entry point.

The same command line a real deployment's CI and a hypothetical external
operator both run (invoked identically by CI
building the default distribution and by a hypothetical external
operator):

- `atlas-compose resolve <manifest> -o <lock>` — manifest -> lock.
- `atlas-compose validate <manifest> <lock>` — static composition
  validation.
- `atlas-compose generate backend <lock> -o <path>` — lock ->
  `SELECTED_PLUGINS` module.
- `atlas-compose generate frontend <lock> -o <path>` — lock ->
  `installedFrontendPlugins` composition module.
"""

import argparse
from pathlib import Path

from .composition import authentication_configuration_diff, validate_composition
from .descriptors import load_backend_descriptors
from .generate import dump_composition_module, dump_selected_plugins_module
from .lock import dump_lock, load_lock
from .manifest import load_manifest
from .resolver import resolve_manifest


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="atlas-compose")
    subparsers = parser.add_subparsers(dest="command", required=True)

    resolve_parser = subparsers.add_parser(
        "resolve",
        help="Resolve a deployment manifest to a lock file.",
    )
    resolve_parser.add_argument("manifest", type=Path)
    resolve_parser.add_argument("-o", "--output", type=Path, required=True)
    resolve_parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Monorepo root containing core/backend/poetry.lock and package-lock.json.",
    )

    validate_parser = subparsers.add_parser(
        "validate",
        help="Run static composition validation for a manifest + lock.",
    )
    validate_parser.add_argument("manifest", type=Path)
    validate_parser.add_argument("lock", type=Path)

    diff_parser = subparsers.add_parser(
        "diff",
        help="Show authentication differences between manifest and lock.",
    )
    diff_parser.add_argument("manifest", type=Path)
    diff_parser.add_argument("lock", type=Path)

    generate_parser = subparsers.add_parser(
        "generate",
        help="Generate the backend/frontend composition modules a lock implies.",
    )
    generate_subparsers = generate_parser.add_subparsers(
        dest="target",
        required=True,
    )
    generate_backend_parser = generate_subparsers.add_parser(
        "backend",
        help="Generate the SELECTED_PLUGINS module.",
    )
    generate_backend_parser.add_argument("lock", type=Path)
    generate_backend_parser.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
    )
    generate_frontend_parser = generate_subparsers.add_parser(
        "frontend",
        help="Generate the installedFrontendPlugins composition module.",
    )
    generate_frontend_parser.add_argument("lock", type=Path)
    generate_frontend_parser.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
    )

    args = parser.parse_args(argv)

    if args.command == "resolve":
        manifest = load_manifest(args.manifest)
        lock = resolve_manifest(manifest, repo_root=args.repo_root)
        dump_lock(lock, args.output)
    elif args.command == "validate":
        manifest = load_manifest(args.manifest)
        lock = load_lock(args.lock)
        descriptors = load_backend_descriptors(lock)
        validate_composition(manifest, lock, descriptors)
        distribution = manifest.distribution
        print(f"{distribution.id}@{distribution.version} composition is valid")
    elif args.command == "diff":
        manifest = load_manifest(args.manifest)
        lock = load_lock(args.lock)
        differences = authentication_configuration_diff(manifest, lock)
        if differences:
            for difference in differences:
                print(f"- {difference}")
        else:
            print("Authentication selection matches the lock")
    elif args.command == "generate":
        lock = load_lock(args.lock)
        if args.target == "backend":
            dump_selected_plugins_module(lock, args.output)
        else:
            dump_composition_module(lock, args.output)


if __name__ == "__main__":
    main()
