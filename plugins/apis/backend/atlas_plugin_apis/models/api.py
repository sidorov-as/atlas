from typing import ClassVar

from atlas_plugin_api import CATALOG_ENTITY_LABEL
from django.db import models


class ApiDetails(models.Model):
    """Kind-specific data for a `CatalogEntity` of kind `api` —
    split out of `server.apps.catalog.models.api`."""

    TYPE_OPENAPI = "openapi"
    TYPE_GRPC = "grpc"
    TYPE_ASYNCAPI = "asyncapi"
    TYPE_GRAPHQL = "graphql"
    TYPE_CHOICES: ClassVar[list] = [
        (TYPE_OPENAPI, "OpenAPI"),
        (TYPE_GRPC, "gRPC"),
        (TYPE_ASYNCAPI, "AsyncAPI"),
        (TYPE_GRAPHQL, "GraphQL"),
    ]

    SPEC_SOURCE_NONE = "none"
    SPEC_SOURCE_INLINE = "inline"
    SPEC_SOURCE_URL = "url"
    SPEC_SOURCE_CHOICES: ClassVar[list] = [
        (SPEC_SOURCE_NONE, "None"),
        (SPEC_SOURCE_INLINE, "Inline"),
        (SPEC_SOURCE_URL, "URL"),
    ]

    entity = models.OneToOneField(
        CATALOG_ENTITY_LABEL,
        primary_key=True,
        on_delete=models.CASCADE,
        related_name="api_details",
    )
    type = models.CharField(max_length=32, choices=TYPE_CHOICES)
    system = models.ForeignKey(
        CATALOG_ENTITY_LABEL, on_delete=models.PROTECT, related_name="apis"
    )
    spec_source = models.CharField(
        max_length=16, choices=SPEC_SOURCE_CHOICES, default=SPEC_SOURCE_NONE
    )
    spec_url = models.URLField(blank=True)
    spec_content = models.TextField(
        blank=True, help_text="Resolved spec snapshot, regardless of source"
    )
    spec_resolved_at = models.DateTimeField(null=True, blank=True)
    spec_resolve_failed = models.BooleanField(default=False)
    endpoints_synced_at = models.DateTimeField(null=True, blank=True)
    endpoints_sync_failed = models.BooleanField(default=False)
    operations_synced_at = models.DateTimeField(null=True, blank=True)
    operations_sync_failed = models.BooleanField(default=False)
    # Resolved from the OpenAPI document's `servers` (3.x) / `host`+`basePath`+
    # `schemes` (2.0) only when unambiguous — left blank otherwise, never
    # guessed among multiple candidates (mirroring `ApiOperation.channel_protocol`'s
    # "unambiguous only" precedent).
    resolved_base_url = models.CharField(max_length=2048, blank=True)
    resolved_protocol = models.CharField(max_length=32, blank=True)

    class Meta:
        # Kept on the pre-existing `catalog` app_label so this physical package
        # move needs no new migration — `catalog`'s existing migration history
        # (`0012_catalog_entity_identity`) already created this table.
        app_label = "catalog"

    def __str__(self) -> str:
        return self.entity.name
