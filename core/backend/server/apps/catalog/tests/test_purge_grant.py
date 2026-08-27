"""`PurgeGrant` model and `has_purge_grant` authorization rule
(catalog-auth/entity-removal-lifecycle specs: "Purge Grant permission,
scoped per owner-Group with a global-admin override")."""

import pytest
from django.db import IntegrityError

from server.apps.catalog.authorization import has_purge_grant
from server.apps.catalog.models import PurgeGrant

pytestmark = pytest.mark.django_db


def test_grant_holder_is_authorized_for_their_scoped_group(
    group,
    owner_account,
):
    PurgeGrant.objects.create(group=group, grantee=owner_account)

    assert has_purge_grant(owner_account, group) is True


def test_grant_does_not_cross_group_boundaries(
    group,
    other_group,
    owner_account,
):
    PurgeGrant.objects.create(group=group, grantee=owner_account)

    assert has_purge_grant(owner_account, other_group) is False


def test_user_with_no_grant_is_not_authorized(group, owner_account):
    assert has_purge_grant(owner_account, group) is False


def test_global_admin_needs_no_grant(group, superuser_account):
    assert has_purge_grant(superuser_account, group) is True


def test_global_admin_needs_no_group_either(superuser_account):
    assert has_purge_grant(superuser_account, None) is True


def test_a_grant_is_unique_per_group_and_grantee(group, owner_account):
    PurgeGrant.objects.create(group=group, grantee=owner_account)

    with pytest.raises(IntegrityError):
        PurgeGrant.objects.create(group=group, grantee=owner_account)
