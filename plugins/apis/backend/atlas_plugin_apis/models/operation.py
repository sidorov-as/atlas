import uuid
from typing import ClassVar

from atlas_plugin_api import CATALOG_ENTITY_LABEL
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models


class ApiOperation(models.Model):
    """A single channel operation of an AsyncAPI `API` document
    plugin-owned child data of the API's `CatalogEntity`, not a registered
    Entity Kind: no `kind_id`, no independent owner/team/tags/visibility of
    its own (it inherits all of that from `api`), and no top-level
    `/catalog/entities/...` route. Mirrors `ApiEndpoint`'s precedent exactly.

    `id` is its own UUID, never derived from `channel_address`/`direction`/
    `operation_key`, so it stays stable — and every
    `ServiceOperationUsage` link pointing at it stays valid — across a
    channel rename. `operation_key` (not `id`) is the business identity used
    for re-import upsert; it is unique per `api`, not globally.

    `direction` is deliberately `send | receive` — AsyncAPI 3.0's own,
    version-agnostic vocabulary — never the raw AsyncAPI 2.x `publish`/
    `subscribe` field names, which are defined from the channel's confusing
    perspective.

    Removal is soft (`status=removed`): existing
    `ServiceOperationUsage` rows are never cascade-deleted when an operation
    goes away, only when its owning API entity itself is deleted.

    `deprecated` is a manual-only
    override, never written by `_upsert_operation` — AsyncAPI's Operation
    Object has no native deprecated keyword (unlike OpenAPI), so this is the
    only way to flag a deprecated Operation, and re-import must never reset
    it.
    """

    DIRECTION_SEND = "send"
    DIRECTION_RECEIVE = "receive"
    DIRECTION_CHOICES: ClassVar[list] = [
        (DIRECTION_SEND, "Send"),
        (DIRECTION_RECEIVE, "Receive"),
    ]

    STATUS_ACTIVE = "active"
    STATUS_REMOVED = "removed"
    STATUS_CHOICES: ClassVar[list] = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_REMOVED, "Removed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    api = models.ForeignKey(
        CATALOG_ENTITY_LABEL, on_delete=models.CASCADE, related_name="operations"
    )
    # The event name shared across APIs. For AMQP documents this is the
    # operation's `cc` routing key (falling back to the channel's own address).
    channel_address = models.CharField(max_length=2048)
    channel_protocol = models.CharField(max_length=64, blank=True)
    direction = models.CharField(max_length=16, choices=DIRECTION_CHOICES)
    # Business identity for re-import upsert: the AsyncAPI 3.0
    # operations-map key, or (for 2.x) `channel key + direction`. Never
    # used as a cross-document join key — only unique within `api`.
    operation_key = models.CharField(max_length=512)
    # Decorative only (spec's optional `operationId`/`title`) — never used
    # for identity, unlike `operation_key`.
    operation_id = models.CharField(max_length=255, blank=True)
    summary = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    tags = ArrayField(models.CharField(max_length=100), default=list, blank=True)
    # One or more message shapes (schema/example) carried by this operation's
    # channel — a provisional, plugin-owned JSON shape with no external
    # contract beyond what `api/schemas.py`'s read models expose, mirroring
    # `ApiEndpoint.request`/`.responses`' precedent.
    message = models.JSONField(default=list, blank=True)
    # `{"description": str, "url": str}`, or `{}` when the Operation Object
    # declares no `externalDocs`.
    external_docs = models.JSONField(default=dict, blank=True)
    # How the event is delivered: any of `{"exchange", "queue", "vhost"}` read
    # from the channel's AMQP bindings, `{}` otherwise. Documentation only — it
    # never takes part in identity or in grouping by `channel_address`.
    delivery = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default=STATUS_ACTIVE
    )
    deprecated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering: ClassVar[list] = ["channel_address", "operation_key"]
        constraints: ClassVar[list] = [
            models.UniqueConstraint(
                "api", "operation_key", name="apioperation_unique_api_operation_key"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.direction} {self.channel_address}"


class ServiceOperationUsage(models.Model):
    """An explicit `Service <-> Operation` link with a role
    a bespoke,
    plugin-owned join, not routed through the core `entity-relations`
    derivation system, mirroring `ServiceEndpointUsage`'s own rationale.

    Unlike `ServiceEndpointUsage`, this link carries an explicit `role`
    (`publisher` | `subscriber`), asserted independently of the linked
    `Operation`'s own `direction` — the two answer different questions (what
    the document declares vs. what a human asserts about some other Service).
    `unique_together(operation, service, role)` allows one Service to hold
    both roles on the same Operation as two distinct rows.

    The Operation's own document-owning Service (found via the `apiProvidedBy`
    relation) is never recorded as a row here — its role is implied purely
    from `Operation.direction` at read time. Rejecting an attempt to
    self-link that Service happens at the view layer, the same
    way duplicate-link rejection does — it depends on resolving the
    `apiProvidedBy` relation, which isn't expressible as a static DB
    constraint on this model alone.

    `operation`'s `on_delete` is moot for the removal path: removing an
    `ApiOperation` is always a `status` update (never a row delete — see
    `ApiOperationAdmin`), so this FK is never actually exercised by that flow.
    """

    ORIGIN_MANUAL = "manual"
    ORIGIN_YAML = "yaml"
    ORIGIN_CHOICES: ClassVar[list] = [
        (ORIGIN_MANUAL, "Manual"),
        (ORIGIN_YAML, "YAML"),
    ]
    SOURCE_UI = "ui"
    SOURCE_MCP = "mcp"
    SOURCE_CHOICES: ClassVar[list] = [
        (SOURCE_UI, "UI"),
        (SOURCE_MCP, "MCP"),
    ]

    ROLE_PUBLISHER = "publisher"
    ROLE_SUBSCRIBER = "subscriber"
    ROLE_CHOICES: ClassVar[list] = [
        (ROLE_PUBLISHER, "Publisher"),
        (ROLE_SUBSCRIBER, "Subscriber"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    operation = models.ForeignKey(
        ApiOperation, on_delete=models.CASCADE, related_name="service_usages"
    )
    service = models.ForeignKey(
        CATALOG_ENTITY_LABEL, on_delete=models.CASCADE, related_name="operation_usages"
    )
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    origin = models.CharField(
        max_length=16, choices=ORIGIN_CHOICES, default=ORIGIN_MANUAL
    )
    source = models.CharField(max_length=16, choices=SOURCE_CHOICES, default=SOURCE_UI)

    class Meta:
        ordering: ClassVar[list] = ["-created_at"]
        constraints: ClassVar[list] = [
            models.UniqueConstraint(
                "operation",
                "service",
                "role",
                name="serviceoperationusage_unique_operation_service_role",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.service} -> {self.operation} ({self.role})"
