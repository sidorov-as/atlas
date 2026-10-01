from atlas_plugin_standard_catalog.api.urls import (
    router as standard_catalog_router,
)
from django.apps import apps
from django.contrib import admin
from django.urls import include, path

from server.apps.catalog.api.urls import router as catalog_router
from server.health import (
    AtlasHealthCheckView,
    AuthenticationProviderHealthView,
    PluginHealthView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("auth/browser/v1/", include("server.apps.catalog.auth_urls")),
    path("_allauth/", include("allauth.headless.urls")),
    # Transitional provider-library login/callback names used by the
    # allauth-backed OIDC/Gitea adapters. AuthenticationPolicyMiddleware
    # selection-gates every request beneath this prefix.
    path("accounts/", include("allauth.urls")),
    path("healthz/", AtlasHealthCheckView.as_view()),
    path("healthz/plugins/", PluginHealthView.as_view()),
    path("healthz/auth/providers/", AuthenticationProviderHealthView.as_view()),
    catalog_router.to_urlpatterns(),
    standard_catalog_router.to_urlpatterns(),
]

if apps.is_installed("atlas_plugin_apis"):
    # unavailable-entity spec: a deselected atlas.apis must make its routes
    # disappear (a clean 404), not 500 — `ApiDetailController`'s queries
    # assume `atlas_plugin_apis`'s model is registered, gated here like
    # `atlas_plugin_c4`/`atlas_plugin_database_schema` below.
    from atlas_plugin_apis.api.urls import router as apis_router

    urlpatterns.append(apis_router.to_urlpatterns())

if apps.is_installed("atlas_plugin_c4"):
    # c4-plugin spec's "Distribution without atlas.c4 composes successfully"
    # scenario requires no diagram endpoints to be registered when the
    # plugin is deselected — unlike the other
    # plugin routers above, gated here rather than unconditionally included.
    from atlas_plugin_c4.api.urls import router as c4_router

    urlpatterns.append(c4_router.to_urlpatterns())

if apps.is_installed("atlas_plugin_database_schema"):
    # database-schema-plugin spec's "Distribution without the plugin composes
    # successfully" scenario requires no facet endpoint to be registered when
    # the plugin is deselected — gated here like `atlas_plugin_c4` above.
    from atlas_plugin_database_schema.api.urls import (
        router as database_schema_router,
    )

    urlpatterns.append(database_schema_router.to_urlpatterns())

if apps.is_installed("atlas_plugin_flows"):
    # flows-plugin spec's "Distribution without atlas.flows composes
    # successfully" scenario requires no `/flows` routes to be registered
    # when the plugin is deselected — gated here like `atlas_plugin_c4`/
    # `atlas_plugin_database_schema` above.
    from atlas_plugin_flows.api.urls import router as flows_router

    urlpatterns.append(flows_router.to_urlpatterns())

if apps.is_installed("atlas_plugin_mcp"):
    # mcp-plugin spec's "Distribution without atlas.mcp composes
    # successfully" scenario requires no MCP-facing routes to be registered
    # when the plugin is deselected — gated here like every other optional
    # plugin's router above. `atlas_plugin_mcp.api.urls.router` is itself
    # built fresh at that module's import time (after every plugin's app is
    # already registered), so its own Flow routes already reflect whether
    # `atlas.flows` is installed in this same distribution.
    from atlas_plugin_mcp.api.urls import router as mcp_router

    urlpatterns.append(mcp_router.to_urlpatterns())
