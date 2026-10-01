"""Fixtures for this package's own test suite — self-contained, matching
`atlas_plugin_c4`/`atlas_plugin_flows`'s own `tests/conftest.py` (see their
docstrings: this plugin's tests live in a separate directory tree, so
pytest's conftest discovery doesn't inherit `core/backend/conftest.py`'s
fixtures).

`pat_plaintext` binds a stub `PATValidator`
(`atlas_plugin_api.pat.bind_pat_validator`) rather than issuing a real token
through Core's own `server.apps.catalog.services.pat_service` — the same
testing seam `atlas_plugin_api.tests.test_auth` uses for `PATBearerAuth`
itself, and the one a third-party plugin author's own tests would use too:
`bind_pat_validator` is this contract's sanctioned test seam, so this
plugin's tests need no Core-internal import to exercise `PATBearerAuth`-
protected controllers (`core/backend/server/apps/plugins/tests/
test_import_boundaries.py`'s "no core internals outside `atlas_plugin_api`"
rule).
"""

import atlas_plugin_api.pat as pat_module
import pytest
from atlas_plugin_api.pat import ResolvedPersonalAccessToken, bind_pat_validator
from django.contrib.auth import get_user_model
from server.apps.catalog.tests.factories import (
    create_actor,
    create_group,
    create_system,
)

_VALID_TOKEN = "atlaspat_mcp-test-token"
_WRITE_SCOPED_TOKEN = "atlaspat_mcp-test-write-token"


@pytest.fixture
def group(db):
    return create_group(name="platform")


@pytest.fixture
def system(db, group):
    return create_system(name="user-management", owner=group)


@pytest.fixture
def owner_account(db):
    return get_user_model().objects.create_user(
        username="owner",
        password="password123",
    )


@pytest.fixture
def owner_user(owner_account, group):
    """`owner_account` as a member of `group` — needed to pass
    `FlowService.create`/`.update`/`.delete`'s own ownership-based write
    permission check (`atlas_plugin_flows.permissions.check_flow_write_permission`)."""
    entity = create_actor(name="owner", account=owner_account)
    group.group_details.members.add(entity)
    return entity


@pytest.fixture
def pat_plaintext(owner_account):
    """A PAT scoped `catalog:read`/`flows:read` only — every read-tool test
    uses this; a write-tool test that expects a *rejection* from an
    insufficiently-scoped token uses this too (`personal-access-tokens`
    spec: "Read-only-scoped PAT cannot perform a write operation").
    """
    previous = pat_module._pat_validator

    def _validator(raw_token: str) -> ResolvedPersonalAccessToken | None:
        if raw_token != _VALID_TOKEN:
            return None
        return ResolvedPersonalAccessToken(
            user=owner_account, scopes=frozenset({"catalog:read", "flows:read"})
        )

    bind_pat_validator(_validator)
    try:
        yield _VALID_TOKEN
    finally:
        pat_module._pat_validator = previous


@pytest.fixture
def pat_auth_header(pat_plaintext):
    return {"HTTP_AUTHORIZATION": f"Bearer {pat_plaintext}"}


@pytest.fixture
def write_scoped_pat_plaintext(owner_user):
    """A PAT carrying every scope a write tool checks
    (`catalog:write`/`flows:write`), alongside the matching read scopes,
    belonging to `owner_user`'s account — a Group member, needed to pass
    the underlying RBAC check (`EntityWritePermission`/
    `check_flow_write_permission`) that a scope-only test isn't exercising.
    A write-tool test asserting success, or an RBAC-denial independent of
    scope, uses this.
    """
    previous = pat_module._pat_validator
    account = owner_user.actor_details.account

    def _validator(raw_token: str) -> ResolvedPersonalAccessToken | None:
        if raw_token != _WRITE_SCOPED_TOKEN:
            return None
        return ResolvedPersonalAccessToken(
            user=account,
            scopes=frozenset(
                {"catalog:read", "catalog:write", "flows:read", "flows:write"}
            ),
        )

    bind_pat_validator(_validator)
    try:
        yield _WRITE_SCOPED_TOKEN
    finally:
        pat_module._pat_validator = previous


@pytest.fixture
def write_scoped_pat_auth_header(write_scoped_pat_plaintext):
    return {"HTTP_AUTHORIZATION": f"Bearer {write_scoped_pat_plaintext}"}


@pytest.fixture
def outsider_account(db):
    """A second account, deliberately never added to `group`'s membership —
    a write-scoped PAT belonging to this user still has every scope a write
    tool checks, so a request it authenticates is denied by the underlying
    user's own RBAC (`EntityWritePermission`/`check_flow_write_permission`),
    not by `require_scope` — the independent-of-scope half of
    `personal-access-tokens`'s "RBAC-denied and scope-denied writes are both
    rejected" bar.
    """
    return get_user_model().objects.create_user(
        username="outsider",
        password="password123",
    )


@pytest.fixture
def outsider_write_scoped_pat_auth_header(outsider_account):
    previous = pat_module._pat_validator
    token = "atlaspat_mcp-test-outsider-write-token"

    def _validator(raw_token: str) -> ResolvedPersonalAccessToken | None:
        if raw_token != token:
            return None
        return ResolvedPersonalAccessToken(
            user=outsider_account,
            scopes=frozenset(
                {"catalog:read", "catalog:write", "flows:read", "flows:write"}
            ),
        )

    bind_pat_validator(_validator)
    try:
        yield {"HTTP_AUTHORIZATION": f"Bearer {token}"}
    finally:
        pat_module._pat_validator = previous
