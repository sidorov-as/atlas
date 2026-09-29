"""Minimal semver-range comparison for compatibility checks
(`">=3.1 <4"`-style ranges, so plugins version independently).

Only the bounded-range shape every `PluginDescriptor.compatibility` entry
in this codebase actually writes is supported — one or two
`<operator><version>` clauses separated by whitespace, all of which must
hold (an implicit AND) — not general semver range syntax (caret/tilde
ranges, OR clauses, pre-release tags). Extend this the day a real range
needs more.
"""

import re

_CLAUSE = re.compile(r"(>=|<=|==|>|<)\s*(\d+(?:\.\d+){0,2})")

_OPERATORS = {
    ">=": lambda version, bound: version >= bound,
    "<=": lambda version, bound: version <= bound,
    ">": lambda version, bound: version > bound,
    "<": lambda version, bound: version < bound,
    "==": lambda version, bound: version == bound,
}


class InvalidRangeError(ValueError):
    def __init__(self, range_expr: str) -> None:
        super().__init__(
            f"{range_expr!r} is not a supported compatibility range",
        )
        self.range_expr = range_expr


def _parse_version(version: str) -> tuple[int, int, int]:
    parts = [int(part) for part in version.split(".")[:3]]
    parts += [0] * (3 - len(parts))
    return parts[0], parts[1], parts[2]


def range_contains(range_expr: str, version: str) -> bool:
    """Whether `version` satisfies every clause of `range_expr`, e.g.
    `range_contains(">=3.1 <4", "3.2.0")` -> `True`."""
    clauses = _CLAUSE.findall(range_expr)
    if not clauses:
        raise InvalidRangeError(range_expr)
    target = _parse_version(version)
    return all(
        _OPERATORS[operator](target, _parse_version(bound))
        for operator, bound in clauses
    )
