"""`is_account_read_only`/`CoreGuardedEvaluator` tests. Full bypass/
regression coverage across every entry point lives in the other suites;
this file covers the shared predicate and the facade mechanism itself.
"""

from unittest.mock import patch

import pytest
from atlas_plugin_api import (
    get_policy_evaluator,
    register_permission,
)
from django.db import Error as DjangoDatabaseError

from server.apps.catalog.authorization import (
    CoreGuardedEvaluator,
    RBACPolicyEvaluator,
    is_account_read_only,
    policy_evaluator,
)
from server.apps.catalog.models import (
    KIND_RESOURCE,
    AccountAccess,
    CatalogEntity,
)


class _StubEvaluator:
    def __init__(self, result: bool) -> None:
        self.result = result
        self.calls = []

    def check(self, principal, permission, resource):
        self.calls.append((principal, permission, resource))
        return self.result


def test_missing_account_access_row_is_not_read_only(owner_account):
    assert is_account_read_only(owner_account) is False


def test_flagged_account_is_read_only(owner_account):
    AccountAccess.objects.create(account=owner_account, read_only=True)

    assert is_account_read_only(owner_account) is True


def test_cleared_flag_is_not_read_only(owner_account):
    AccountAccess.objects.create(account=owner_account, read_only=False)

    assert is_account_read_only(owner_account) is False


def test_database_error_fails_closed(owner_account):
    target = "server.apps.catalog.authorization.AccountAccess.objects.filter"
    with patch(target, side_effect=DjangoDatabaseError):
        assert is_account_read_only(owner_account) is True


def test_anonymous_principal_is_not_read_only():
    assert is_account_read_only(None) is False


def test_non_read_only_principal_is_delegated(owner_account):
    inner = _StubEvaluator(result=True)
    guarded = CoreGuardedEvaluator(inner)

    assert guarded.check(owner_account, f"{KIND_RESOURCE}.edit", None) is True
    assert inner.calls == [(owner_account, f"{KIND_RESOURCE}.edit", None)]


def test_read_only_principal_read_permission_is_delegated(owner_account):
    AccountAccess.objects.create(account=owner_account, read_only=True)
    inner = _StubEvaluator(result=True)
    guarded = CoreGuardedEvaluator(inner)

    assert guarded.check(owner_account, f"{KIND_RESOURCE}.read", None) is True
    assert len(inner.calls) == 1


def test_read_only_status_does_not_grant_a_denied_read_permission(
    owner_account,
):
    AccountAccess.objects.create(account=owner_account, read_only=True)
    inner = _StubEvaluator(result=False)
    guarded = CoreGuardedEvaluator(inner)

    assert (
        guarded.check(
            owner_account,
            f"{KIND_RESOURCE}.read",
            None,
        )
        is False
    )
    assert len(inner.calls) == 1


def test_read_only_principal_write_is_denied_before_delegation(owner_account):
    """A read-only write is denied even if an alternate evaluator would
    permit it — a permissive inner evaluator never runs.
    """
    AccountAccess.objects.create(account=owner_account, read_only=True)
    inner = _StubEvaluator(result=True)
    guarded = CoreGuardedEvaluator(inner)

    permission = f"{KIND_RESOURCE}.edit"
    assert guarded.check(owner_account, permission, None) is False
    assert inner.calls == []


def test_read_only_principal_unknown_permission_is_denied(owner_account):
    AccountAccess.objects.create(account=owner_account, read_only=True)
    inner = _StubEvaluator(result=True)
    guarded = CoreGuardedEvaluator(inner)

    permission = "atlas.some-plugin.widget.sync"
    assert guarded.check(owner_account, permission, None) is False
    assert inner.calls == []


@pytest.mark.parametrize("suffix", ["execute", "sync"])
def test_read_only_principal_nonstandard_write_defaults_are_denied(
    owner_account,
    suffix,
):
    AccountAccess.objects.create(account=owner_account, read_only=True)
    permission = f"atlas.test-fixture.read-only-{suffix}.{suffix}"
    register_permission(permission, owner="atlas.test-fixture")
    inner = _StubEvaluator(result=True)

    assert (
        CoreGuardedEvaluator(inner).check(
            owner_account,
            permission,
            None,
        )
        is False
    )
    assert inner.calls == []


def test_explicit_nonstandard_read_effect_is_delegated(owner_account):
    AccountAccess.objects.create(account=owner_account, read_only=True)
    permission = "atlas.test-fixture.read-only-query.query"
    register_permission(
        permission,
        owner="atlas.test-fixture",
        effect="read",
    )
    inner = _StubEvaluator(result=True)

    assert (
        CoreGuardedEvaluator(inner).check(
            owner_account,
            permission,
            None,
        )
        is True
    )
    assert inner.calls == [(owner_account, permission, None)]


def test_public_plugin_lookup_returns_the_core_guarded_evaluator():
    assert get_policy_evaluator() is policy_evaluator


def test_read_only_superuser_purge_denied_before_shortcut(
    superuser_account,
    group,
):
    """A read-only superuser's purge request is denied —
    exercised against the real `RBACPolicyEvaluator`/
    `has_purge_grant`, not a stub, so the superuser shortcut inside
    `has_purge_grant` is proven unreachable, not merely un-mocked.
    """
    AccountAccess.objects.create(account=superuser_account, read_only=True)
    resource = CatalogEntity.objects.create(
        kind=KIND_RESOURCE,
        name="r",
        owner=group,
    )
    guarded = CoreGuardedEvaluator(RBACPolicyEvaluator())

    permission = f"{KIND_RESOURCE}.purge"
    assert guarded.check(superuser_account, permission, resource) is False
