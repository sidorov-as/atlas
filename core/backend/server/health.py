"""Application-specific health-check configuration."""

from dataclasses import asdict
from urllib.parse import urljoin
from uuid import uuid4

from atlas_plugin_api import get_authentication_provider_lookup
from django.http import JsonResponse
from django.urls import reverse
from django.views import View
from health_check.views import HealthCheckView

from server.apps.catalog.auth_policy import authentication_policy
from server.apps.plugins.health import plugin_health


class AtlasHealthCheckView(HealthCheckView):
    """Run the standard checks except filesystem storage."""

    checks = tuple(
        check
        for check in HealthCheckView.checks
        if check != "health_check.checks.Storage"
    )


class PluginHealthView(View):
    """Per-plugin diagnostics (`runtime-failure-isolation` spec): reports
    each selected plugin's status, distinguishing `active` from `disabled`
    and `degraded`."""

    def get(self, request):
        plugins = [asdict(status) for status in plugin_health()]
        has_degraded = any(plugin["status"] == "degraded" for plugin in plugins)
        return JsonResponse(
            {"plugins": plugins},
            status=503 if has_degraded else 200,
        )


class AuthenticationProviderHealthView(View):
    """Independent, allowlist-shaped selected-provider diagnostics."""

    def get(self, request):
        policy = authentication_policy()
        lookup = get_authentication_provider_lookup()
        correlation_id = str(uuid4())
        providers = []
        unavailable = False
        for selected in policy.get("providers", ()):
            provider_id = selected.get("id")
            runtime = lookup.get(provider_id)
            status = "available"
            category = "ok"
            if runtime is None:
                status, category = "unavailable", "not_registered"
            else:
                health = getattr(runtime, "health", None)
                if callable(health):
                    try:
                        result = health()
                    except Exception:
                        status, category = "unavailable", "check_failed"
                    else:
                        if isinstance(result, dict):
                            status = (
                                "available"
                                if result.get("status") == "available"
                                else "unavailable"
                            )
                            category = str(result.get("category", "unknown"))
            unavailable = unavailable or status != "available"
            origin = str(policy.get("publicOrigin", ""))
            callback_path = reverse(
                "atlas-auth-provider-callback",
                kwargs={"provider_id": provider_id},
            )
            providers.append(
                {
                    "providerId": provider_id,
                    "selected": True,
                    "default": provider_id == policy.get("default"),
                    "flowKind": selected.get("flowKind"),
                    "status": status,
                    "category": category,
                    "callbackUrl": urljoin(
                        origin.rstrip("/") + "/", callback_path.lstrip("/")
                    ),
                    "correlationId": correlation_id,
                }
            )
        response = JsonResponse(
            {"providers": providers, "correlationId": correlation_id},
            status=503 if unavailable else 200,
        )
        response.headers["Cache-Control"] = "no-store"
        return response
