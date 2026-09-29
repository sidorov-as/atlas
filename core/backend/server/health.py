"""Application-specific health-check configuration."""

import logging
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

logger = logging.getLogger(__name__)

_EXCLUDED_CHECKS = frozenset(
    {"health_check.checks.Storage", "health_check.checks.DNS"}
)


class AtlasHealthCheckView(HealthCheckView):
    """Run the standard checks except filesystem storage and DNS.

    The DNS check resolves the container's own hostname, which platforms such
    as Render do not publish, so it fails on a perfectly healthy service.

    A failing check makes the endpoint answer 500 without saying which one,
    and platform probes never ask for `?format=json`, so name each failure in
    the application log.
    """

    checks = tuple(
        check
        for check in HealthCheckView.checks
        if check not in _EXCLUDED_CHECKS
    )

    async def get(self, request, *args, **kwargs):
        response = await super().get(request, *args, **kwargs)
        for result in self.results:
            if result.error:
                logger.error(
                    "Health check failed: %s: %s (%.3fs)",
                    result.check,
                    result.error,
                    result.time_taken,
                )
        return response


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
