"""Development-only fixture authentication provider.

This package is intentionally not part of Atlas's production dependencies or
default distribution.  Its public surface exists solely for the runnable
custom-provider example.
"""

from .config import FixtureCredentialConfig

__all__ = ["FixtureCredentialConfig"]
