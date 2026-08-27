"""Atlas-owned django-allauth policy adapter."""

from __future__ import annotations

from typing import Any

from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser
from django.core.exceptions import ValidationError

from .auth_policy import (
    local_authentication_selected,
    local_signup_open,
    verified_recovery_addresses_required,
)


class AtlasAccountAdapter(DefaultAccountAdapter):
    """Apply generated selection/signup policy at the server boundary."""

    def is_open_for_signup(self, request) -> bool:
        return local_signup_open()

    def authenticate(
        self,
        request,
        **credentials: Any,
    ) -> AbstractBaseUser | None:
        if not local_authentication_selected():
            # Use the same public error as invalid credentials: selection state
            # must not become an account-existence oracle.
            self.pre_authenticate(request, **credentials)
            self.authentication_failed(request, **credentials)
            return None
        return super().authenticate(request, **credentials)

    def clean_password(
        self,
        password: str,
        user: AbstractBaseUser | None = None,
    ) -> str:
        maximum = getattr(settings, "ATLAS_PASSWORD_MAXIMUM_LENGTH", 128)
        if len(password) > maximum:
            raise ValidationError(
                "This password is too long. It must contain at most "
                f"{maximum} characters.",
                code="password_too_long",
            )
        return super().clean_password(password, user=user)

    def post_login(self, request, user, **kwargs):
        request._atlas_auth_provider = "atlas.auth.local"
        return super().post_login(request, user, **kwargs)

    def send_password_reset_mail(self, user, email: str, context) -> None:
        if verified_recovery_addresses_required():
            verified = EmailAddress.objects.filter(
                user=user,
                email__iexact=email,
                verified=True,
            ).exists()
            if not verified:
                return
        return super().send_password_reset_mail(user, email, context)
