"""Permission-check plumbing for `atlas.c4.diagram.read`

Repointed at the real, pluggable `PolicyEvaluator` singleton extension point
via `atlas_plugin_api.get_policy_evaluator()`
this plugin no longer
carries its own stand-in evaluator (`AlwaysAllowIfAuthenticated`), nor does
it import Core's `server.apps.catalog.authorization` directly. No
`CatalogEntity` resource is available at the point this check runs (it
happens before the diagram's target entity is resolved, and the System
Landscape diagram has no single target entity at all), so it requests a
decision with `resource=None`; the built-in RBAC evaluator treats any
`*.read` permission as granted to any authenticated principal regardless of
resource, matching today's exact pre-existing behavior (any authenticated
session may read any diagram — no diagram ACL exists).
"""

from http import HTTPStatus

from atlas_plugin_api import get_policy_evaluator
from django.contrib.auth.base_user import AbstractBaseUser
from dmr.errors import ErrorType, format_error
from dmr.response import APIError

from .plugin import DIAGRAM_READ_PERMISSION


def check_diagram_read_permission(user: AbstractBaseUser) -> None:
    if not get_policy_evaluator().check(user, DIAGRAM_READ_PERMISSION, None):
        raise APIError(
            format_error(
                "You do not have permission to read diagrams",
                error_type=ErrorType.security,
            ),
            status_code=HTTPStatus.FORBIDDEN,
        )
