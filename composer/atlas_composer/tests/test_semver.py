"""Compatibility-range comparison tests (`composition-validation` spec)."""

import pytest

from atlas_composer.semver import InvalidRangeError, range_contains


@pytest.mark.parametrize(
    ("range_expr", "version", "expected"),
    [
        (">=0.1 <1", "0.1.0", True),
        (">=0.1 <1", "0.9.9", True),
        (">=0.1 <1", "1.0.0", False),
        (">=0.1 <1", "0.0.9", False),
        (">=3.1 <4", "3.2.0", True),
        (">=3.1 <4", "3.1", True),
        (">=3.1 <4", "4.0.0", False),
        ("==2.3.1", "2.3.1", True),
        ("==2.3.1", "2.3.2", False),
    ],
)
def test_range_contains(range_expr, version, expected):
    assert range_contains(range_expr, version) is expected


def test_range_contains_rejects_an_unparseable_range():
    with pytest.raises(InvalidRangeError):
        range_contains("whatever", "1.0.0")
