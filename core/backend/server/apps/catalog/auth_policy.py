"""Authoritative runtime access to the generated authentication policy."""

from __future__ import annotations

from typing import Any

from django.conf import settings

LOCAL_PROVIDER_ID = "atlas.auth.local"
LOCAL_SOURCE_ID = "urn:atlas:local"


def authentication_policy() -> dict[str, Any]:
    """Return generated policy, failing closed when generation is absent."""

    policy = getattr(settings, "ATLAS_AUTHENTICATION", None)
    return policy if isinstance(policy, dict) else {}


def selected_provider(provider_id: str) -> dict[str, Any] | None:
    for provider in authentication_policy().get("providers", ()):
        if provider.get("id") == provider_id:
            return provider
    return None


def provider_source_id(provider: dict[str, Any]) -> str | None:
    if provider.get("id") == LOCAL_PROVIDER_ID:
        return LOCAL_SOURCE_ID
    binding = provider.get("sourceBinding")
    if not isinstance(binding, dict):
        return None
    source_id = binding.get("sourceId")
    return source_id if isinstance(source_id, str) and source_id else None


def local_authentication_selected() -> bool:
    return selected_provider(LOCAL_PROVIDER_ID) is not None


def local_signup_open() -> bool:
    provider = selected_provider(LOCAL_PROVIDER_ID)
    return bool(provider and provider.get("signup") == "enabled")


def public_recovery_enabled() -> bool:
    recovery = authentication_policy().get("recovery", {})
    return recovery.get("mode") == "public"


def verified_recovery_addresses_required() -> bool:
    recovery = authentication_policy().get("recovery", {})
    return recovery.get("verifiedAddressesRequired", True) is True


def admin_password_principal_ids() -> frozenset[int]:
    admin = authentication_policy().get("adminPassword", {})
    if admin.get("mode") != "break-glass":
        return frozenset()
    return frozenset(admin.get("principalIds", ()))


def admin_password_allowed(user: Any) -> bool:
    return bool(
        user
        and user.pk in admin_password_principal_ids()
        and user.is_active
        and user.is_staff
    )


def session_max_age_seconds() -> int:
    value = authentication_policy().get("sessionMaxAgeSeconds", 28_800)
    return value if isinstance(value, int) and value > 0 else 28_800


def public_authentication_config() -> dict[str, Any]:
    policy = authentication_policy()
    providers = []
    for provider in policy.get("providers", ()):
        presentation = provider.get("presentation", {})
        item: dict[str, Any] = {
            "id": provider["id"],
            "contractVersion": provider.get(
                "contractVersion", "atlas.auth.providers.v1"
            ),
            "flowKind": provider.get("flowKind"),
            "presentation": {
                "displayName": presentation.get("displayName", provider["id"]),
            },
            "remoteLogout": provider.get("remoteLogout", "unsupported"),
            "isDefault": provider["id"] == policy.get("default"),
        }
        credential_fields = presentation.get("credentialFields")
        if credential_fields:
            item["presentation"]["credentialFields"] = credential_fields
        if provider["id"] == LOCAL_PROVIDER_ID:
            item["signupOpen"] = local_signup_open()
        providers.append(item)
    return {
        "providers": providers,
        "defaultProviderId": policy.get("default"),
        "providerChoiceUrl": "/login?choose-provider=1",
    }
