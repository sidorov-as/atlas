"""Personal Access Token issuance and validation (`personal-access-tokens`
spec).

`validate_personal_access_token` is the function Core hands to
`atlas_plugin_api.pat.bind_pat_validator()` in `plugin.register_runtime()`
— its return type (`atlas_plugin_api.pat.ResolvedPersonalAccessToken`) is
the same ORM-free dataclass `atlas_plugin_api.auth.PATBearerAuth` consumes,
so this module is the only place that ever touches `PersonalAccessToken`'s
own fields on the read path.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from atlas_plugin_api.pat import ResolvedPersonalAccessToken
from django.db import transaction
from django.utils import timezone

from server.apps.catalog.models import (
    LOOKUP_PREFIX_LENGTH,
    TOKEN_SECRET_PREFIX,
    PersonalAccessToken,
    generate_token_secret,
    hash_token_secret,
)


@dataclass(frozen=True)
class IssuedPersonalAccessToken:
    """Returned once, at issuance, by `issue_personal_access_token` — the
    only place the plaintext ever exists outside the issuer's own clipboard
    (`personal-access-tokens` spec: "the plaintext value is displayed once
    in that response, and no later request ... can retrieve it again").
    """

    instance: PersonalAccessToken
    plaintext: str


def issue_personal_access_token(
    *,
    owner: Any,
    name: str = "",
    scopes: Iterable[str] = (),
    expires_at: datetime | None = None,
) -> IssuedPersonalAccessToken:
    """Issue a new PAT for `owner`. Only `token_hash` and `prefix` are
    persisted — the returned `plaintext` is never stored anywhere,
    matching `PersonalAccessToken`'s own "hash + prefix, never plaintext
    at rest" contract.
    """
    secret = generate_token_secret()
    instance = PersonalAccessToken.objects.create(
        owner=owner,
        name=name,
        prefix=secret[:LOOKUP_PREFIX_LENGTH],
        token_hash=hash_token_secret(secret),
        scopes=list(scopes),
        expires_at=expires_at,
    )
    return IssuedPersonalAccessToken(
        instance=instance, plaintext=f"{TOKEN_SECRET_PREFIX}{secret}"
    )


def validate_personal_access_token(
    raw_token: str,
) -> ResolvedPersonalAccessToken | None:
    """Resolve a raw `Authorization: Bearer <token>` value to its owning
    user and scopes, or `None` if it doesn't exist, doesn't hash-match, is
    expired/revoked, or its owning account is no longer active
    (`PersonalAccessToken.is_currently_valid`). Updates `last_used_at` as a
    side effect of a successful resolution (`personal-access-tokens` spec:
    "Token usage is tracked").
    """
    if not raw_token.startswith(TOKEN_SECRET_PREFIX):
        return None
    secret = raw_token[len(TOKEN_SECRET_PREFIX) :]
    prefix = secret[:LOOKUP_PREFIX_LENGTH]
    token_hash = hash_token_secret(secret)

    token: PersonalAccessToken
    try:
        token = PersonalAccessToken.objects.select_related("owner").get(
            prefix=prefix, token_hash=token_hash
        )
    except PersonalAccessToken.DoesNotExist:
        return None

    if not token.is_currently_valid():
        return None

    with transaction.atomic():
        PersonalAccessToken.objects.filter(pk=token.pk).update(
            last_used_at=timezone.now()
        )

    return ResolvedPersonalAccessToken(
        user=token.owner, scopes=frozenset(token.scopes)
    )
