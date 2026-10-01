#!/usr/bin/env python3
"""Structural check for the `skills/` collection.

Fails (exit 1) when a skill folder has no `SKILL.md`, when its frontmatter is
not valid YAML, lacks a `name` equal to the folder name or a non-empty
`description`, or when any relative Markdown link inside `skills/` points at a
file that does not exist (including paths into another skill's `references/`).

Usage: python scripts/check_skills.py [skills_dir]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "#")


def read_frontmatter(path: Path) -> tuple[dict | None, str | None]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, "missing frontmatter (file must start with '---')"
    try:
        end = next(i for i, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration:
        return None, "frontmatter is not closed with '---'"
    try:
        data = yaml.safe_load("\n".join(lines[1:end]))
    except yaml.YAMLError as exc:
        return None, f"frontmatter is not valid YAML: {exc}"
    if not isinstance(data, dict):
        return None, "frontmatter is not a mapping"
    return data, None


def check_skill(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.is_file():
        return [f"{skill_dir.name}: SKILL.md is missing"]
    data, error = read_frontmatter(skill_file)
    if error:
        return [f"{skill_dir.name}: {error}"]
    assert data is not None
    if data.get("name") != skill_dir.name:
        errors.append(
            f"{skill_dir.name}: frontmatter name {data.get('name')!r} "
            f"does not match the folder name"
        )
    description = data.get("description")
    if not isinstance(description, str) or not description.strip():
        errors.append(f"{skill_dir.name}: frontmatter description is missing or empty")
    return errors


def check_links(root: Path) -> list[str]:
    errors: list[str] = []
    for md in sorted(root.rglob("*.md")):
        in_fence = False
        for number, line in enumerate(md.read_text(encoding="utf-8").splitlines(), 1):
            if FENCE_RE.match(line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for target in LINK_RE.findall(line):
                if target.startswith(EXTERNAL_PREFIXES):
                    continue
                path = target.split("#", 1)[0]
                if not path:
                    continue
                if not (md.parent / path).resolve().exists():
                    rel = md.relative_to(root.parent)
                    errors.append(f"{rel}:{number}: broken reference {target!r}")
    return errors


def main(argv: list[str]) -> int:
    root = Path(argv[1] if len(argv) > 1 else "skills")
    if not root.is_dir():
        print(f"skills directory not found: {root}", file=sys.stderr)
        return 1
    skill_dirs = sorted(p for p in root.iterdir() if p.is_dir())
    if not skill_dirs:
        print(f"no skill folders under {root}", file=sys.stderr)
        return 1
    errors: list[str] = []
    for skill_dir in skill_dirs:
        errors.extend(check_skill(skill_dir))
    errors.extend(check_links(root))
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"Skills check passed ({len(skill_dirs)} skills)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
