"""Session metadata, audit logging, and credential-change revocation."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from allauth.account.signals import password_changed, password_reset
from django.contrib.auth.signals import user_logged_in
from django.contrib.sessions.models import Session
from django.dispatch import receiver

from .auth_middleware import (
    AUTHENTICATED_AT_KEY,
    IDENTITY_LINK_GENERATION_KEY,
    IDENTITY_LINK_KEY,
    POLICY_GENERATION_KEY,
    PRINCIPAL_GENERATION_KEY,
    PROVIDER_KEY,
    SOURCE_GENERATION_KEY,
    SOURCE_KEY,
)
from .auth_policy import session_max_age_seconds
from .auth_security import (
    current_policy_generation,
    principal_generation,
    revoke_principal_sessions,
    source_binding_generation,
)

log = structlog.get_logger(__name__)


@receiver(user_logged_in, dispatch_uid="atlas.authentication.session_metadata")
def record_session_metadata(sender, request, user, **kwargs) -> None:
    provider_id = getattr(request, "_atlas_auth_provider", "atlas.auth.local")
    request.session[PROVIDER_KEY] = provider_id
    request.session[AUTHENTICATED_AT_KEY] = datetime.now(UTC).timestamp()
    source_id = getattr(request, "_atlas_auth_source", None)
    identity_link = getattr(request, "_atlas_auth_identity_link", None)
    if source_id is not None:
        request.session[SOURCE_KEY] = source_id
        request.session[SOURCE_GENERATION_KEY] = source_binding_generation(
            provider_id, source_id
        )
    if identity_link is not None:
        request.session[IDENTITY_LINK_KEY] = identity_link.pk
        request.session[IDENTITY_LINK_GENERATION_KEY] = (
            identity_link.revocation_generation
        )
    request.session[POLICY_GENERATION_KEY] = current_policy_generation()
    request.session[PRINCIPAL_GENERATION_KEY] = principal_generation(user)
    request.session.set_expiry(session_max_age_seconds())
    log.info(
        "authentication_succeeded",
        principal_id=user.pk,
        provider_id=provider_id,
    )


def _revoke_user_sessions(user) -> None:
    for session in Session.objects.all().iterator():
        try:
            user_id = session.get_decoded().get("_auth_user_id")
        except Exception:
            # A corrupt/expired session cannot authorize anything.
            continue
        if str(user_id) == str(user.pk):
            session.delete()


@receiver(password_reset, dispatch_uid="atlas.authentication.password_reset")
@receiver(
    password_changed,
    dispatch_uid="atlas.authentication.password_changed",
)
def revoke_sessions_after_credential_change(
    sender,
    request,
    user,
    **kwargs,
) -> None:
    revoke_principal_sessions(user)
    _revoke_user_sessions(user)
    log.info("authentication_sessions_revoked", principal_id=user.pk)
