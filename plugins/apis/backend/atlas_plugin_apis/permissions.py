"""Permission-check plumbing for `atlas.apis.endpoint.read` and
`atlas.apis.endpointDependency.read`/`.create`/`.delete`
plus
`atlas.apis.endpoint.purge`/`atlas.apis.operation.purge`

Same shape as `atlas_plugin_c4.permissions.check_diagram_read_permission`:
neither `Endpoint` nor `ServiceEndpointUsage` has an owner of its own
so the `.read` checks are requested with
`resource=None`; the built-in RBAC evaluator treats `*.read` as granted to
any authenticated principal regardless of resource
(`server.apps.catalog.authorization.RBACPolicyEvaluator`).

The `.create`/`.delete` checks are requested with `resource=<the consuming
Service>`, not `resource=None` (prerelease security audit finding: a bare
`resource=None` let any authenticated user link or unlink any Service to any
Endpoint/Operation, including ones owned by unrelated teams).
`RBACPolicyEvaluator` scopes `.create`/`.delete` to `is_group_member` against
that resource's owner, same as `.edit` — so the check is "does this principal
own the Service being (un)linked," never membership in the Endpoint/
Operation's own owner Group, which would wrongly require joining another
team's Group just to declare your Service depends on their API.

The `.purge` checks are the other exception: `Endpoint`/`Operation` inherit
their owner from the parent `api` entity, so the purge check is requested
with `resource=api` — `RBACPolicyEvaluator` routes any `.purge`-suffixed
permission through `has_purge_grant(principal, resource.owner)`, scoping the
grant to the API's owning Group the same way whole-entity Purge is scoped.
"""

from http import HTTPStatus

from atlas_plugin_api import CatalogEntity, get_policy_evaluator
from django.contrib.auth.base_user import AbstractBaseUser
from dmr.errors import ErrorType, format_error
from dmr.response import APIError

from .plugin import (
    ENDPOINT_DEPENDENCY_CREATE_PERMISSION,
    ENDPOINT_DEPENDENCY_DELETE_PERMISSION,
    ENDPOINT_DEPENDENCY_READ_PERMISSION,
    ENDPOINT_PURGE_PERMISSION,
    ENDPOINT_READ_PERMISSION,
    OPERATION_DEPENDENCY_CREATE_PERMISSION,
    OPERATION_DEPENDENCY_DELETE_PERMISSION,
    OPERATION_DEPENDENCY_READ_PERMISSION,
    OPERATION_PURGE_PERMISSION,
    OPERATION_READ_PERMISSION,
)


def _require(
    user: AbstractBaseUser,
    permission: str,
    message: str,
    resource: CatalogEntity | None = None,
) -> None:
    if not get_policy_evaluator().check(user, permission, resource):
        raise APIError(
            format_error(message, error_type=ErrorType.security),
            status_code=HTTPStatus.FORBIDDEN,
        )


def check_endpoint_read_permission(user: AbstractBaseUser) -> None:
    _require(
        user,
        ENDPOINT_READ_PERMISSION,
        "You do not have permission to read endpoints",
    )


def check_endpoint_purge_permission(user: AbstractBaseUser, api: CatalogEntity) -> None:
    _require(
        user,
        ENDPOINT_PURGE_PERMISSION,
        "You do not hold a Purge Grant for this Endpoint's API's owner Group",
        resource=api,
    )


def check_endpoint_dependency_read_permission(user: AbstractBaseUser) -> None:
    _require(
        user,
        ENDPOINT_DEPENDENCY_READ_PERMISSION,
        "You do not have permission to read endpoint dependencies",
    )


def check_endpoint_dependency_create_permission(
    user: AbstractBaseUser, service: CatalogEntity
) -> None:
    _require(
        user,
        ENDPOINT_DEPENDENCY_CREATE_PERMISSION,
        "You do not have permission to link this Service to an Endpoint",
        resource=service,
    )


def check_endpoint_dependency_delete_permission(
    user: AbstractBaseUser, service: CatalogEntity
) -> None:
    _require(
        user,
        ENDPOINT_DEPENDENCY_DELETE_PERMISSION,
        "You do not have permission to unlink this Service from an Endpoint",
        resource=service,
    )


def check_operation_read_permission(user: AbstractBaseUser) -> None:
    _require(
        user,
        OPERATION_READ_PERMISSION,
        "You do not have permission to read operations",
    )


def check_operation_purge_permission(
    user: AbstractBaseUser, api: CatalogEntity
) -> None:
    _require(
        user,
        OPERATION_PURGE_PERMISSION,
        "You do not hold a Purge Grant for this Operation's API's owner Group",
        resource=api,
    )


def check_operation_dependency_read_permission(user: AbstractBaseUser) -> None:
    _require(
        user,
        OPERATION_DEPENDENCY_READ_PERMISSION,
        "You do not have permission to read operation dependencies",
    )


def check_operation_dependency_create_permission(
    user: AbstractBaseUser, service: CatalogEntity
) -> None:
    _require(
        user,
        OPERATION_DEPENDENCY_CREATE_PERMISSION,
        "You do not have permission to link this Service to an Operation",
        resource=service,
    )


def check_operation_dependency_delete_permission(
    user: AbstractBaseUser, service: CatalogEntity
) -> None:
    _require(
        user,
        OPERATION_DEPENDENCY_DELETE_PERMISSION,
        "You do not have permission to unlink this Service from an Operation",
        resource=service,
    )
