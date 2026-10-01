"""Personal Access Token issuance/validation tests (`personal-access-tokens`
spec).

`test_pat_scopes_never_broaden_owner_rbac` additionally proves the
"narrows, never broadens" half of the spec end to end: a PAT that carries a
scope covering an operation is still rejected once its *owner's* RBAC would
reject that same operation — resolving a PAT never substitutes for, or
adds to, the real actor's own permissions, since `PATBearerAuth`/
`validate_personal_access_token` only ever resolve *which* Django user is
acting, and every write still runs through that user's own RBAC exactly as
it would for a session-authenticated request.
"""

from datetime import timedelta
from http import HTTPStatus

import pytest
from atlas_plugin_flows.contracts import FlowIn
from atlas_plugin_flows.extension_points import get_flow_service
from django.utils import timezone
from dmr.response import APIError

from server.apps.catalog.models import PersonalAccessToken
from server.apps.catalog.services.pat_service import (
    issue_personal_access_token,
    validate_personal_access_token,
)

pytestmark = pytest.mark.django_db


def test_issuing_a_token_displays_plaintext_once_and_persists_hash_only(
    owner_account,
):
    issued = issue_personal_access_token(
        owner=owner_account, name="ci", scopes=["catalog:read"]
    )

    assert issued.plaintext.startswith("atlaspat_")
    assert len(issued.plaintext) > len("atlaspat_")

    stored = PersonalAccessToken.objects.get(pk=issued.instance.pk)
    assert stored.token_hash != issued.plaintext
    assert issued.plaintext not in stored.token_hash
    assert stored.prefix and stored.prefix in issued.plaintext


def test_validate_personal_access_token_resolves_owner_and_scopes(
    owner_account,
):
    issued = issue_personal_access_token(
        owner=owner_account, scopes=["catalog:read", "flows:write"]
    )

    resolved = validate_personal_access_token(issued.plaintext)

    assert resolved is not None
    assert resolved.user == owner_account
    assert resolved.scopes == frozenset({"catalog:read", "flows:write"})


def test_validate_personal_access_token_rejects_unknown_token():
    assert validate_personal_access_token("atlaspat_does-not-exist") is None


def test_validate_personal_access_token_rejects_malformed_token():
    assert validate_personal_access_token("not-an-atlas-token") is None


def test_validate_personal_access_token_rejects_expired_token(owner_account):
    issued = issue_personal_access_token(
        owner=owner_account, expires_at=timezone.now() - timedelta(seconds=1)
    )

    assert validate_personal_access_token(issued.plaintext) is None


def test_validate_personal_access_token_rejects_revoked_token(owner_account):
    issued = issue_personal_access_token(owner=owner_account)
    issued.instance.revoked_at = timezone.now()
    issued.instance.save(update_fields=["revoked_at"])

    assert validate_personal_access_token(issued.plaintext) is None


def test_validate_personal_access_token_rejects_deactivated_owner(
    owner_account,
):
    """Rejected even though the token itself is neither expired nor
    revoked (`personal-access-tokens` spec: "independent of the token's
    own `expires_at`/`revoked_at` values")."""
    issued = issue_personal_access_token(owner=owner_account)
    owner_account.is_active = False
    owner_account.save(update_fields=["is_active"])

    assert validate_personal_access_token(issued.plaintext) is None


def test_successful_validation_updates_last_used_at(owner_account):
    issued = issue_personal_access_token(owner=owner_account)
    assert issued.instance.last_used_at is None

    before = timezone.now()
    resolved = validate_personal_access_token(issued.plaintext)
    assert resolved is not None

    issued.instance.refresh_from_db()
    assert issued.instance.last_used_at is not None
    assert issued.instance.last_used_at >= before


def test_pat_scopes_never_broaden_owner_rbac(other_account, system):
    """A PAT scoped for `flows:write` still cannot write a Flow under a
    system its owner doesn't belong to — the token's scope narrows, but
    never broadens, `other_account`'s own RBAC (`personal-access-tokens`
    spec: "A token SHALL NOT grant an operation its owning user could not
    otherwise perform").
    """
    issued = issue_personal_access_token(
        owner=other_account, scopes=["flows:write"]
    )
    resolved = validate_personal_access_token(issued.plaintext)
    assert resolved is not None

    with pytest.raises(APIError) as exc_info:
        get_flow_service().create(
            body=FlowIn(system="system:user-management", name="pat-scope-flow"),
            actor=resolved.user,
        )
    assert exc_info.value.status_code == HTTPStatus.FORBIDDEN
