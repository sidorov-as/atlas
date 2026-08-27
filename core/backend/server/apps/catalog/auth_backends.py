"""Django authentication backends that enforce Atlas selection policy."""

from allauth.account.auth_backends import AuthenticationBackend
from django.contrib.auth.backends import ModelBackend

from .auth_policy import admin_password_allowed


class AtlasModelBackend(ModelBackend):
    """Allow Django-admin passwords only for explicit break-glass accounts."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        # allauth uses its own backend for catalog credential authentication.
        # The model backend remains available solely for the Django admin.
        if request is None or not request.path.startswith("/admin/"):
            return None
        user = super().authenticate(
            request,
            username=username,
            password=password,
            **kwargs,
        )
        if not admin_password_allowed(user):
            return None
        request._atlas_auth_provider = "atlas.auth.admin-password"
        return user


class AtlasAllauthAuthenticationBackend(AuthenticationBackend):
    """Prevent allauth's model-like backend bypassing admin break-glass."""

    def authenticate(self, request, **credentials):
        if request is not None and request.path.startswith("/admin/"):
            return None
        return super().authenticate(request, **credentials)
