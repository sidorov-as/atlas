"""Startup orchestration.

The single path `manage.py`, `wsgi.py`, and `asgi.py` all call before
handing control to Django:

    read selected static descriptors
      -> verify identities
      -> generate INSTALLED_APPS
      -> django.setup()
      -> load selected runtime entry points
      -> assemble capability, permission, and Entity Kind registries
      -> validate composition
      -> accept traffic

(plugin-architecture.md:390-399). The static phase (read/verify/generate
`INSTALLED_APPS`) runs as a side effect of `server.settings` being
imported, below; the runtime phase (load entry points, assemble
registries, validate composition) runs inside `PluginsConfig.ready()`,
itself invoked by `django.setup()`.

A failure anywhere in that chain — an invalid/duplicate plugin identity,
or a duplicate capability/permission/kind id — is logged here and turned
into a non-zero exit, before the process ever binds a listening port
"""

import logging
import os
import sys

from server.apps.plugins.composition import CompositionError
from server.apps.plugins.resolver import (
    InvalidPluginDescriptorError,
    MissingPluginDescriptorError,
)

logger = logging.getLogger("server.apps.plugins")

# The static phase can fail with either of these before `django.setup()`
# even starts populating apps; the runtime phase fails composition with
# `CompositionError`. None of the three imports Django models at module
# level, so all three are safe to import here, ahead of `django.setup()`.
_STATIC_PHASE_ERRORS = (
    InvalidPluginDescriptorError,
    MissingPluginDescriptorError,
)


def bootstrap() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.settings")

    import re
    import warnings

    import django
    from django.db.backends.utils import CursorWrapper

    # django.contrib.postgres.apps.PostgresConfig.ready() queries pg_type
    # for hstore/array OIDs on every startup — a real, expected DB access
    # during app init, not a bug. Under the dev server's `-W error` it would
    # otherwise be fatal before django.setup() even finishes.
    warnings.filterwarnings(
        "default",
        message=re.escape(CursorWrapper.APPS_NOT_READY_WARNING_MSG),
        category=RuntimeWarning,
    )

    try:
        django.setup()
    except _STATIC_PHASE_ERRORS as exc:
        logger.error(
            "Backend startup failed: invalid plugin selection: %s",
            exc,
        )
        sys.exit(1)
    except CompositionError as exc:
        logger.error("Backend startup failed during composition: %s", exc)
        sys.exit(1)

    _log_startup_summary()


def _log_startup_summary() -> None:
    from django.conf import settings

    from server.apps.catalog.kinds.registry import registry as kind_registry
    from server.apps.plugins.capabilities import registry as capability_registry
    from server.apps.plugins.permissions import registry as permission_registry

    logger.info(
        "Backend startup complete: installed_apps=%s capability_ids=%s "
        "permission_ids=%s kind_ids=%s",
        list(settings.INSTALLED_APPS),
        capability_registry.registered_ids(),
        permission_registry.registered_ids(),
        kind_registry.registered_ids(),
    )
