import uuid
from typing import ClassVar

from atlas_plugin_api import CATALOG_ENTITY_LABEL
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models


class ApiEndpoint(models.Model):
    """A single operation (method + path) of an `API` — plugin-owned child data of the API's
    `CatalogEntity`, not a registered Entity Kind: no `kind_id`, no
    independent owner/team/tags/visibility of its own (it inherits all of
    that from `api`), and no top-level `/catalog/entities/...` route.

    `id` is its own UUID, never derived from `method`/`path`, so
    it stays stable — and every `ServiceEndpointUsage` link pointing at it
    stays valid — across a path edit. Removal is soft (`status=removed`):
    existing `ServiceEndpointUsage` rows are never cascade-
    deleted when an endpoint goes away, only when its owning API entity itself
    is deleted.
    """

    METHOD_GET = "GET"
    METHOD_POST = "POST"
    METHOD_PUT = "PUT"
    METHOD_PATCH = "PATCH"
    METHOD_DELETE = "DELETE"
    METHOD_HEAD = "HEAD"
    METHOD_OPTIONS = "OPTIONS"
    METHOD_CHOICES: ClassVar[list] = [
        (METHOD_GET, "GET"),
        (METHOD_POST, "POST"),
        (METHOD_PUT, "PUT"),
        (METHOD_PATCH, "PATCH"),
        (METHOD_DELETE, "DELETE"),
        (METHOD_HEAD, "HEAD"),
        (METHOD_OPTIONS, "OPTIONS"),
    ]

    STATUS_ACTIVE = "active"
    STATUS_REMOVED = "removed"
    STATUS_CHOICES: ClassVar[list] = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_REMOVED, "Removed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    api = models.ForeignKey(
        CATALOG_ENTITY_LABEL, on_delete=models.CASCADE, related_name="endpoints"
    )
    method = models.CharField(max_length=16, choices=METHOD_CHOICES)
    path = models.CharField(max_length=2048)
    operation_id = models.CharField(max_length=255, blank=True)
    summary = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    deprecated = models.BooleanField(default=False)
    tags = ArrayField(models.CharField(max_length=100), default=list, blank=True)
    # Structured, provisional shapes (parameters/body/schema/example) — no
    # external contract promised beyond what `api/schemas.py`'s read models
    # expose (mirrors `DatabaseSchema.parsed_schema`'s precedent for a
    # provisional JSON shape owned entirely by this plugin).
    request = models.JSONField(default=dict, blank=True)
    responses = models.JSONField(default=list, blank=True)
    # `{"description": str, "url": str}`, or `{}` when the operation declares
    # no `externalDocs` — mirrors `ApiOperation.external_docs`'s precedent exactly.
    external_docs = models.JSONField(default=dict, blank=True)
    # A resolved `[{"type": str, "scheme": str | None}, ...]` list — the
    # operation's effective `security` requirement (its own, or the
    # document-level fallback) resolved against `components.securitySchemes`/
    # `securityDefinitions`, not the raw scheme names.
    security = models.JSONField(default=list, blank=True)
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default=STATUS_ACTIVE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering: ClassVar[list] = ["path", "method"]
        constraints: ClassVar[list] = [
            models.UniqueConstraint(
                "api", "method", "path", name="apiendpoint_unique_api_method_path"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.method} {self.path}"


class ServiceEndpointUsage(models.Model):
    """An explicit `Service consumesEndpoint Endpoint` link — a bespoke, plugin-owned join,
    not routed through the core `entity-relations` derivation system, since
    it needs its own search/filter/sort/paginate query shape and a dedicated
    consumers-graph projection that the generic relations endpoint doesn't
    support.

    `endpoint`'s `on_delete` is moot for the removal path: removing an
    `ApiEndpoint` is always a `status` update (never a row delete — see
    `ApiEndpointAdmin`), so this FK is never actually exercised by that flow.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    endpoint = models.ForeignKey(
        ApiEndpoint, on_delete=models.CASCADE, related_name="service_usages"
    )
    service = models.ForeignKey(
        CATALOG_ENTITY_LABEL, on_delete=models.CASCADE, related_name="endpoint_usages"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        ordering: ClassVar[list] = ["-created_at"]
        constraints: ClassVar[list] = [
            models.UniqueConstraint(
                "endpoint",
                "service",
                name="serviceendpointusage_unique_endpoint_service",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.service} -> {self.endpoint}"
