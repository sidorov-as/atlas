"""Permission-check plumbing for `atlas.flows.flow.edit`.

Flow's create/update/delete all resolve an existing `system` first, so a
resource is always available at check time — checked against it directly
through `RBACPolicyEvaluator`'s kind-agnostic `.edit` branch (ownership of
`resource.owner`), the same shape `EntityWritePermission.check_write` used
before this extraction.
"""

from http import HTTPStatus

from atlas_plugin_api import CatalogEntity, get_policy_evaluator
from django.contrib.auth.base_user import AbstractBaseUser
from dmr.errors import ErrorType, format_error
from dmr.response import APIError

FLOW_EDIT_PERMISSION = "atlas.flows.flow.edit"
FLOW_READ_PERMISSION = "atlas.flows.flow.read"


def can_edit_flow(user: AbstractBaseUser, system: CatalogEntity) -> bool:
    return bool(get_policy_evaluator().check(user, FLOW_EDIT_PERMISSION, system))


def check_flow_write_permission(user: AbstractBaseUser, system: CatalogEntity) -> None:
    if not can_edit_flow(user, system):
        raise APIError(
            format_error(
                "You are not a member of the owner Group", error_type=ErrorType.security
            ),
            status_code=HTTPStatus.FORBIDDEN,
        )
