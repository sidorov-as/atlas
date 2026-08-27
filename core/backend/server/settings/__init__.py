"""Template-aligned split Django settings."""

from os import environ

import django_stubs_ext
from split_settings.tools import include

django_stubs_ext.monkeypatch()

environ.setdefault("DJANGO_ENV", "development")
include(
    "components/common.py",
    "components/logging.py",
    "components/csp.py",
    "components/api.py",
    f"environments/{environ['DJANGO_ENV']}.py",
)
