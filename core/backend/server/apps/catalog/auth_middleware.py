"""Compatibility-route and established-session authentication policy."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from django.contrib.auth import logout
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils.cache import patch_cache_control

from .auth_policy import (
    admin_password_allowed,
    public_authentication_config,
    public_recovery_enabled,
    selected_provider,
    session_max_age_seconds,
)

AUTHENTICATED_AT_KEY = "atlas_authenticated_at"
PROVIDER_KEY = "atlas_auth_provider"
SOURCE_KEY = "atlas_auth_source"
IDENTITY_LINK_KEY = "atlas_auth_identity_link_id"
IDENTITY_LINK_GENERATION_KEY = "atlas_auth_identity_link_generation"
SOURCE_GENERATION_KEY = "atlas_auth_source_generation"
POLICY_GENERATION_KEY = "atlas_auth_policy_generation"
PRINCIPAL_GENERATION_KEY = "atlas_auth_principal_generation"

_RECOVERY_PATHS = (
    "/_allauth/browser/v1/auth/password/",
    "/_allauth/browser/v1/account/",
)
_ALLAUTH_PROVIDER_REDIRECT = "/_allauth/browser/v1/auth/provider/redirect"
_ALLAUTH_CONFIG = "/_allauth/browser/v1/config"
_BLOCKED_PROVIDER_COMPATIBILITY_PATHS = frozenset(
    {
        "/_allauth/browser/v1/account/providers",
        "/_allauth/browser/v1/auth/provider/signup",
        "/_allauth/browser/v1/auth/provider/token",
    }
)
_PROVIDER_ROUTE_PREFIXES = {
    "/accounts/oidc/": "atlas.auth.oidc",
    "/accounts/gitea/": "atlas.auth.gitea",
}
_COMPATIBILITY_PROVIDER_IDS = {
    "gitea": "atlas.auth.gitea",
}


class AuthenticationPolicyMiddleware:
    def __init__(self, get_response) -> None:
        self.get_response = get_response

    def __call__(self, request):
        limited = self._rate_limit_authentication_request(request)
        if limited is not None:
            return limited
        if request.path == _ALLAUTH_CONFIG and request.method == "GET":
            get_token(request)
            providers = [
                {
                    "id": item["id"],
                    "name": item["presentation"]["displayName"],
                }
                for item in public_authentication_config()["providers"]
                if item["flowKind"] == "redirect"
            ]
            return self._protected_response(
                JsonResponse(
                    {"data": {"socialaccount": {"providers": providers}}}
                )
            )
        if request.path in _BLOCKED_PROVIDER_COMPATIBILITY_PATHS:
            return self._protected_response(
                JsonResponse({"detail": "Not found."}, status=404)
            )
        recovery_path = request.path.startswith(_RECOVERY_PATHS)
        if recovery_path and not public_recovery_enabled():
            return self._protected_response(
                JsonResponse({"detail": "Not found."}, status=404)
            )

        provider_id = self._compatibility_provider_id(request)
        if provider_id is not None:
            provider = selected_provider(provider_id)
            if provider is None or provider.get("flowKind") != "redirect":
                return self._protected_response(
                    JsonResponse(
                        {"detail": "Authentication provider is not available."},
                        status=404,
                    )
                )

        session_invalid = (
            request.user.is_authenticated
            and not self._session_is_valid(request)
        )
        if session_invalid:
            logout(request)
            return self._protected_response(
                JsonResponse(
                    {"detail": "Authentication session is no longer valid."},
                    status=401,
                )
            )
        response = self.get_response(request)
        if request.path.startswith(("/auth/", "/_allauth/", "/accounts/")):
            self._protected_response(response)
        if "/callback/" in request.path or request.path.endswith("/callback"):
            response.headers["Referrer-Policy"] = "no-referrer"
            # Provider code has already consumed request.GET. Prevent outer
            # server/access-log layers from recording code/state query values.
            request.META["QUERY_STRING"] = ""
        return response

    @staticmethod
    def _protected_response(response):
        patch_cache_control(
            response,
            no_cache=True,
            no_store=True,
            must_revalidate=True,
            private=True,
        )
        return response

    @staticmethod
    def _compatibility_provider_id(request) -> str | None:
        is_provider_redirect = (
            request.path == _ALLAUTH_PROVIDER_REDIRECT
            and request.method == "POST"
        )
        if is_provider_redirect:
            provider_id = request.POST.get("provider")
            is_json = request.content_type == "application/json"
            if provider_id is None and is_json:
                try:
                    body = json.loads(request.body or b"{}")
                except (TypeError, ValueError, UnicodeDecodeError):
                    body = {}
                provider_id = (
                    body.get("provider") if isinstance(body, dict) else None
                )
            if not isinstance(provider_id, str):
                return None
            return _COMPATIBILITY_PROVIDER_IDS.get(provider_id, provider_id)
        for prefix, provider_id in _PROVIDER_ROUTE_PREFIXES.items():
            if request.path.startswith(prefix):
                return provider_id
        return None

    @staticmethod
    def _session_is_valid(request) -> bool:
        from .auth_security import current_policy_generation
        from .models import (
            AuthenticationPrincipalState,
            AuthenticationSourceBinding,
            ExternalIdentityLink,
        )

        provider_id = request.session.get(PROVIDER_KEY)
        authenticated_at = request.session.get(AUTHENTICATED_AT_KEY)
        if provider_id is None or authenticated_at is None:
            return False
        if not request.user.is_active:
            return False
        if provider_id == "atlas.auth.admin-password":
            if not admin_password_allowed(request.user):
                return False
        elif selected_provider(provider_id) is None:
            return False
        try:
            now = datetime.now(UTC).timestamp()
            age = now - float(authenticated_at)
        except (TypeError, ValueError):
            return False
        if not 0 <= age <= session_max_age_seconds():
            return False
        if (
            request.session.get(POLICY_GENERATION_KEY)
            != current_policy_generation()
        ):
            return False
        principal_generation = (
            AuthenticationPrincipalState.objects.filter(user=request.user)
            .values_list("revocation_generation", flat=True)
            .first()
        )
        if request.session.get(PRINCIPAL_GENERATION_KEY) != (
            principal_generation or 0
        ):
            return False
        if provider_id in {"atlas.auth.local", "atlas.auth.admin-password"}:
            return True
        source_id = request.session.get(SOURCE_KEY)
        source_generation = request.session.get(SOURCE_GENERATION_KEY)
        binding = AuthenticationSourceBinding.objects.filter(
            provider_id=provider_id,
            source_id=source_id,
            revoked_at__isnull=True,
        ).first()
        if binding is None or binding.generation != source_generation:
            return False
        link = ExternalIdentityLink.objects.filter(
            pk=request.session.get(IDENTITY_LINK_KEY),
            user=request.user,
            provider_id=provider_id,
            source_id=source_id,
            revoked_at__isnull=True,
        ).first()
        return bool(
            link
            and link.revocation_generation
            == request.session.get(IDENTITY_LINK_GENERATION_KEY)
        )

    @staticmethod
    def _rate_limit_authentication_request(request):
        """Share one budget across framework compatibility auth routes."""

        is_mutation = request.method in {"POST", "PUT", "PATCH", "DELETE"}
        is_callback = request.method == "GET" and "/callback" in request.path
        if not (is_mutation or is_callback):
            return None
        if request.path.startswith("/auth/browser/v1/providers/"):
            # Core gateway applies the same limiter with the exact provider id.
            return None
        if not request.path.startswith(
            ("/auth/", "/_allauth/", "/accounts/", "/admin/login")
        ):
            return None
        from .auth_security import authentication_budget_allowed

        provider_id = (
            AuthenticationPolicyMiddleware._compatibility_provider_id(request)
            or "atlas.auth.local"
        )
        allowed, retry_after = authentication_budget_allowed(
            request, provider_id=provider_id
        )
        if allowed:
            return None
        response = JsonResponse(
            {
                "error": {
                    "category": "rate_limited",
                    "stage": "authentication",
                    "retryable": True,
                }
            },
            status=429,
        )
        response.headers["Retry-After"] = str(retry_after)
        return AuthenticationPolicyMiddleware._protected_response(response)
