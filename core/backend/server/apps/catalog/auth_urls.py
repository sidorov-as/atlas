from django.urls import path

from .auth_gateway import (
    authentication_config,
    authentication_session,
    provider_callback,
    provider_credentials,
    provider_start,
    signup,
)

urlpatterns = [
    path("config", authentication_config, name="atlas-auth-config"),
    path("session", authentication_session, name="atlas-auth-session"),
    path(
        "providers/<str:provider_id>/credentials",
        provider_credentials,
        name="atlas-auth-provider-credentials",
    ),
    path(
        "providers/<str:provider_id>/start",
        provider_start,
        name="atlas-auth-provider-start",
    ),
    path(
        "providers/<str:provider_id>/callback",
        provider_callback,
        name="atlas-auth-provider-callback",
    ),
    path("signup", signup, name="atlas-auth-signup"),
]
