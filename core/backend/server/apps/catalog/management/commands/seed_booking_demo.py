"""Wipe the database and repopulate it with a booking-platform demo catalog.

Models a booking.com/Airbnb-style product: 6 internal Systems (search, booking,
payments, listings, identity, notifications) plus one `External`-tagged System
bundling third-party integrations (Stripe, a maps provider, a tax/compliance
provider, Twilio), and 5 Flows walking through search, booking, cancellation,
payout, and listing publish.

Writes go through the same model layer the HTTP API uses (`ensure_tags_exist`,
`post_save`/`m2m_changed` signals recomputing `Relation` rows) rather than
real HTTP requests, since `Group`/`User` have no creation API and must be
seeded outside it anyway (see `seed_admin`).
"""

import os

from atlas_plugin_apis.models import (
    ApiDetails,
    ApiEndpoint,
    ApiOperation,
    ServiceEndpointUsage,
    ServiceOperationUsage,
)
from atlas_plugin_database_schema.models import DatabaseSchema
from atlas_plugin_database_schema.parser import parse_schema
from atlas_plugin_flows.models import Flow
from atlas_plugin_standard_catalog.extension_points import add_consumed_api
from atlas_plugin_standard_catalog.models import (
    ActorDetails,
    ComponentDetails,
    GroupDetails,
    ResourceDetails,
    SystemDetails,
)
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from server.apps.catalog.management.commands.demo.documentation import (
    documentation_for,
)
from server.apps.catalog.models import (
    KIND_ACTOR,
    KIND_API,
    KIND_COMPONENT,
    KIND_GROUP,
    KIND_RESOURCE,
    KIND_SYSTEM,
    ArchitectureRelationship,
    CatalogEntity,
)
from server.apps.catalog.models.tag import TAG_PALETTE, Tag, ensure_tags_exist

EXTERNAL = ["External"]
TAG_COLOR_CHOICES = tuple(color for color in TAG_PALETTE if color != "gray")

TAG_COLOR_MAP = {
    "Celery": "green",
    "Python": "yellow",
    "FastAPI": "green",
    "PostgreSQL": "blue",
    "Redis": "red",
}


def _yaml_scalar(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return f'"{value}"'
    if value is None:
        return "null"
    return str(value)


def _yaml_properties(fields: dict[str, dict], indent: int) -> str:
    """Render each `fields` entry as a `components.schemas` property block
    (`type`/`format`/`enum`/`description`/`example`), indented `indent`
    spaces."""
    pad = " " * indent
    lines = []
    for name, field_spec in fields.items():
        lines.append(f"{pad}{name}:")
        lines.append(f"{pad}  type: {field_spec['type']}")
        if "format" in field_spec:
            lines.append(f"{pad}  format: {field_spec['format']}")
        if "enum" in field_spec:
            enum_items = ", ".join(
                _yaml_scalar(value) for value in field_spec["enum"]
            )
            lines.append(f"{pad}  enum: [{enum_items}]")
        if "description" in field_spec:
            lines.append(
                f"{pad}  description: {_yaml_scalar(field_spec['description'])}"
            )
        if "example" in field_spec:
            lines.append(
                f"{pad}  example: {_yaml_scalar(field_spec['example'])}"
            )
    return "\n".join(lines)


def _yaml_example(values: dict[str, object], indent: int) -> str:
    pad = " " * indent
    return "\n".join(
        f"{pad}{name}: {_yaml_scalar(value)}" for name, value in values.items()
    )


def openapi_spec(
    title: str,
    resource: str,
    singular: str,
    identifier: str,
    fields: dict[str, dict] | None = None,
) -> str:
    """Return an OpenAPI document for a demo HTTP API — a `components.schemas`
    resource object (resolved via `$ref` into the list/create/get-by-id
    responses) plus a shared `Error` schema for
    404s, richer than a bare id/status shape (`test-api`'s hand-authored
    `User Service API` is the richness this generic template now approaches,
    for every demo API built from `API_RESOURCE_SHAPES` rather than just one).
    `fields` are the resource's own properties beyond `id`/`status` — see
    `API_RESOURCE_SHAPES` for the per-API shape. Also carries a document-level
    `BearerAuth` security requirement, a `status` query parameter with an
    `enum`, a `uuid`-`format` path parameter, a response header, and an
    operation-level `externalDocs` link, so every demo API exercises the
    OpenAPI-derived fields (`_template_endpoints` below
    mirrors the parameter/header shapes so the hand-authored upsert doesn't
    wipe them)."""
    fields = fields or {}
    schema_name = "".join(part.title() for part in singular.split())
    not_found_type = f"{singular.replace(' ', '_')}_not_found"

    properties_block = _yaml_properties(fields, 8)
    required_extra = "\n".join(f"        - {name}" for name in fields)
    field_examples = {
        name: field_spec["example"]
        for name, field_spec in fields.items()
        if "example" in field_spec
    }
    example_block = _yaml_example(field_examples, 16)
    create_example_block = _yaml_example(field_examples, 14)
    list_item_extra_block = _yaml_example(field_examples, 20)

    return f"""openapi: 3.0.3
info:
  title: {title}
  version: 1.0.0
  description: Demo contract for the booking-platform catalog.
servers:
  - url: https://api.demo.atlas.local/v1
security:
  - BearerAuth: []
tags:
  - name: {schema_name}
    description: Operations related to {resource}.
paths:
  /{resource}:
    get:
      operationId: list{schema_name}s
      summary: List {resource}
      tags: [{schema_name}]
      parameters:
        - in: query
          name: status
          required: false
          description: Filter by status
          schema:
            type: string
            enum: [active, archived]
      responses:
        '200':
          description: A page of {resource}
          headers:
            X-Total-Count:
              description: Total number of items available
              schema:
                type: integer
          content:
            application/json:
              schema:
                type: object
                properties:
                  items:
                    type: array
                    items:
                      $ref: "#/components/schemas/{schema_name}"
                  next_cursor:
                    type: string
                    nullable: true
              example:
                items:
                  - id: {identifier}_123
                    status: active
{list_item_extra_block}
                next_cursor: null
    post:
      operationId: create{schema_name}
      summary: Create a {singular}
      tags: [{schema_name}]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/{schema_name}"
            example:
{create_example_block}
      responses:
        '201':
          description: Created
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/{schema_name}"
              example:
                id: {identifier}_123
                status: active
{example_block}
  /{resource}/{{id}}:
    get:
      operationId: get{schema_name}
      summary: Get a {singular} by ID
      tags: [{schema_name}]
      externalDocs:
        description: {title} documentation
        url: https://docs.company.example.com/{resource}
      parameters:
        - in: path
          name: id
          required: true
          description: {singular.title()} ID
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Found
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/{schema_name}"
              example:
                id: {identifier}_123
                status: active
{example_block}
        '404':
          description: Not found
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/Error"
              example:
                type: {not_found_type}
                title: {singular.title()} not found
                status: 404
                detail: Requested {singular} does not exist
components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
  schemas:
    {schema_name}:
      type: object
      title: {schema_name}
      required:
        - id
        - status
{required_extra}
      properties:
        id:
          type: string
          description: Unique identifier.
          example: {identifier}_123
        status:
          type: string
          enum: [active, archived]
          example: active
{properties_block}
    Error:
      type: object
      required:
        - type
        - title
        - status
      properties:
        type:
          type: string
          description: Machine-readable error identifier.
        title:
          type: string
        status:
          type: integer
        detail:
          type: string
"""


def _template_endpoints(
    api: str,
    resource: str,
    singular: str,
    identifier: str,
    fields: dict[str, dict],
) -> list[dict]:
    """`ApiEndpoint` docs for the generic `GET/POST /{resource}` + `GET
    /{resource}/{id}` operations `openapi_spec()` already writes into that API's
    spec text, for the same `(resource, singular, identifier, fields)` shape
    (`API_RESOURCE_SHAPES`) — kept in sync by construction rather than parsed
    from the spec, so this hand-authored text may drift from what
    `atlas_plugin_apis.openapi_import` would itself produce for the same spec
    text (a known, accepted gap, not
    fixed here). `_create_endpoints` upserts these on top of whatever the
    importer already wrote via `ApiDetails`'s `post_save` signal, so this
    hand-authored text always wins."""
    properties = {"id": {"type": "string"}, "status": {"type": "string"}}
    for name, field_spec in fields.items():
        prop: dict[str, object] = {"type": field_spec["type"]}
        for key in ("format", "enum", "description"):
            if key in field_spec:
                prop[key] = field_spec[key]
        properties[name] = prop
    item_schema = {
        "type": "object",
        "properties": properties,
        "required": ["id", "status", *fields],
    }
    error_schema = {
        "type": "object",
        "properties": {
            "type": {"type": "string"},
            "title": {"type": "string"},
            "status": {"type": "integer"},
            "detail": {"type": "string"},
        },
    }
    field_examples = {
        name: field_spec["example"]
        for name, field_spec in fields.items()
        if "example" in field_spec
    }
    example_item = {
        "id": f"{identifier}_123",
        "status": "active",
        **field_examples,
    }
    not_found_type = f"{singular.replace(' ', '_')}_not_found"
    operation = singular.title().replace(" ", "")
    return [
        {
            "api": api,
            "method": "GET",
            "path": f"/{resource}",
            "operation_id": f"list{operation}s",
            "summary": f"List {resource}",
            "tags": [operation],
            "request": {
                "parameters": [
                    {
                        "name": "status",
                        "location": "query",
                        "required": False,
                        "description": "Filter by status",
                        "schema": {
                            "type": "string",
                            "enum": ["active", "archived"],
                        },
                    },
                ],
            },
            "responses": [
                {
                    "status_code": "200",
                    "description": f"A page of {resource}",
                    "content_type": "application/json",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "items": {"type": "array", "items": item_schema},
                            "next_cursor": {"type": "string", "nullable": True},
                        },
                    },
                    "example": {"items": [example_item], "next_cursor": None},
                    "headers": {
                        "X-Total-Count": {
                            "description": "Total number of items available",
                            "schema": {"type": "integer"},
                        },
                    },
                },
            ],
        },
        {
            "api": api,
            "method": "POST",
            "path": f"/{resource}",
            "operation_id": f"create{operation}",
            "summary": f"Create a {singular}",
            "tags": [operation],
            "request": {
                "body": {
                    "content_type": "application/json",
                    "schema": item_schema,
                    "example": field_examples,
                }
            },
            "responses": [
                {
                    "status_code": "201",
                    "description": "Created",
                    "content_type": "application/json",
                    "schema": item_schema,
                    "example": example_item,
                },
            ],
        },
        {
            "api": api,
            "method": "GET",
            "path": f"/{resource}/{{id}}",
            "operation_id": f"get{operation}",
            "summary": f"Get a {singular} by ID",
            "tags": [operation],
            "request": {
                "parameters": [
                    {
                        "name": "id",
                        "location": "path",
                        "required": True,
                        "description": f"{singular.title()} ID",
                        "schema": {"type": "string", "format": "uuid"},
                    },
                ],
            },
            "responses": [
                {
                    "status_code": "200",
                    "description": "Found",
                    "content_type": "application/json",
                    "schema": item_schema,
                    "example": example_item,
                },
                {
                    "status_code": "404",
                    "description": "Not found",
                    "content_type": "application/json",
                    "schema": error_schema,
                    "example": {
                        "type": not_found_type,
                        "title": f"{singular.title()} not found",
                        "status": 404,
                        "detail": f"Requested {singular} does not exist",
                    },
                },
            ],
        },
    ]


ASYNCAPI_SPEC = """asyncapi: 2.6.0
info:
  title: Notifications API
  version: 1.2.0
  description: |
    Events published by the booking platform notification service, plus the
    delivery-status updates it publishes back once a notification has been
    attempted.
  contact:
    name: Notifications Team
    email: notifications-team@example.com
servers:
  production:
    url: broker.demo.atlas.local:9092
    protocol: kafka
    description: Production Kafka cluster
channels:
  booking.confirmed:
    publish:
      operationId: onBookingConfirmed
      summary: Receive booking-confirmation events.
      description: Consumed to notify the guest and host once a booking
        is confirmed.
      tags:
        - name: bookings
      externalDocs:
        description: Booking-confirmation event reference
        url: https://docs.example.com/events/booking-confirmed
      message:
        $ref: "#/components/messages/BookingConfirmed"
  payout.completed:
    publish:
      operationId: onPayoutCompleted
      summary: Receive host-payout notifications.
      description: Consumed to notify a host once their payout has been
        completed.
      tags:
        - name: payouts
      message:
        $ref: "#/components/messages/PayoutCompleted"
  notification.delivery-status:
    subscribe:
      operationId: publishDeliveryStatus
      summary: Publish a delivery-status update.
      description: Published once a transactional notification has been
        attempted, so other services can track delivery.
      tags:
        - name: notifications
      message:
        $ref: "#/components/messages/DeliveryStatus"
  refund.issued:
    publish:
      operationId: onRefundIssued
      summary: Receive refund-issued events.
      description: Consumed to notify the guest once a refund has been
        issued for a cancelled booking.
      tags:
        - name: refunds
      message:
        $ref: "#/components/messages/RefundIssued"
components:
  messages:
    BookingConfirmed:
      name: BookingConfirmed
      title: Booking Confirmed
      summary: A booking has been confirmed and is ready to notify.
      contentType: application/json
      headers:
        $ref: "#/components/schemas/EventHeaders"
      payload:
        $ref: "#/components/schemas/BookingConfirmedPayload"
      examples:
        - payload:
            booking_id: booking_af31
            guest_id: guest_456
            channel: email
            listing:
              id: listing_9f2a
              title: Sunny loft near the marina
    PayoutCompleted:
      name: PayoutCompleted
      title: Payout Completed
      summary: A host payout has completed successfully.
      contentType: application/json
      payload:
        $ref: "#/components/schemas/PayoutCompletedPayload"
      examples:
        - payload:
            payout_id: payout_772c
            host_id: host_772c
            amount: 892.15
            currency: USD
    DeliveryStatus:
      name: DeliveryStatus
      title: Delivery Status
      summary: A transactional notification has been attempted.
      contentType: application/json
      payload:
        $ref: "#/components/schemas/DeliveryStatusPayload"
      examples:
        - payload:
            notification_id: notification_9d21
            status: delivered
            channel: email
    RefundIssued:
      name: RefundIssued
      title: Refund Issued
      summary: A refund has been issued for a cancelled booking.
      contentType: application/json
      payload:
        # Sibling key next to a `$ref` — AsyncAPI's Reference Object semantics
        # discard it (`spec_refs.resolve_schema`'s `merge_siblings=False`
        # default), unlike OpenAPI where an equivalent sibling would be merged
        # onto the resolved schema. The Message tab's Payload section shows
        # `RefundIssuedPayload`'s own description below, not this one.
        $ref: "#/components/schemas/RefundIssuedPayload"
        description: "Sibling override next to $ref (discarded, not merged,
          for AsyncAPI)"
      examples:
        - payload:
            refund_id: refund_9c21
            booking_id: booking_af31
            amount: 149.5
            currency: USD
  schemas:
    EventHeaders:
      type: object
      title: Event envelope headers
      description: Common envelope headers carried alongside a
        notification event's payload.
      required: [message_id, correlation_id]
      properties:
        message_id:
          type: string
          format: uuid
          description: Unique identifier for this message.
          example: 3fa85f64-5717-4562-b3fc-2c963f66afa6
        correlation_id:
          type: string
          description: Identifier correlating this event with the request
            that triggered it.
          example: corr_af31
    BookingConfirmedPayload:
      type: object
      title: BookingConfirmed payload
      description: Payload of the booking-confirmation domain event.
      required: [booking_id, guest_id, channel]
      properties:
        booking_id:
          type: string
          description: Booking that was confirmed.
          example: booking_af31
        guest_id:
          type: string
          description: Guest the booking belongs to.
          example: guest_456
        channel:
          type: string
          description: Delivery channel to notify the guest through.
          enum: [email, sms, push]
          example: email
        listing:
          $ref: "#/components/schemas/ListingSummary"
    PayoutCompletedPayload:
      type: object
      title: PayoutCompleted payload
      required: [payout_id, host_id, amount]
      properties:
        payout_id:
          type: string
          example: payout_772c
        host_id:
          type: string
          example: host_772c
        amount:
          type: number
          format: double
          example: 892.15
        currency:
          type: string
          example: USD
    DeliveryStatusPayload:
      type: object
      title: DeliveryStatus payload
      required: [notification_id, status]
      properties:
        notification_id:
          type: string
          example: notification_9d21
        status:
          type: string
          enum: [queued, sent, delivered, failed]
          example: delivered
        channel:
          type: string
          enum: [email, sms, push]
          example: email
    ListingSummary:
      type: object
      title: Listing summary
      description: A minimal snapshot of the listing a booking was made for.
      properties:
        id:
          type: string
          example: listing_9f2a
        title:
          type: string
          example: Sunny loft near the marina
    RefundIssuedPayload:
      type: object
      title: RefundIssued payload
      description: Payload of the refund-issued domain event.
      required: [refund_id, booking_id, amount]
      properties:
        refund_id:
          type: string
          example: refund_9c21
        booking_id:
          type: string
          example: booking_af31
        amount:
          type: number
          format: double
          example: 149.5
        currency:
          type: string
          example: USD
"""

# A second, independently-authored `asyncapi`-typed API sharing a real channel
# address with `ASYNCAPI_SPEC` above (`booking.confirmed`) — the "one channel
# with operations from two
# different API documents" case, exercising the channel-aggregated graph and
# grouped list with real seed data
# rather than just the empty-state fallback.
BOOKING_EVENTS_ASYNCAPI_SPEC = """asyncapi: 2.6.0
info:
  title: Booking Events API
  version: 1.1.0
  description: Booking lifecycle events published by the booking service.
servers:
  production:
    url: broker.demo.atlas.local:9092
    protocol: kafka
channels:
  booking.confirmed:
    subscribe:
      operationId: publishBookingConfirmed
      summary: Publish booking-confirmation events.
      description: Published once a booking is confirmed, for any downstream
        consumer of the event.
      tags:
        - name: bookings
      message:
        $ref: "#/components/messages/BookingConfirmed"
  booking.cancelled:
    subscribe:
      operationId: publishBookingCancelled
      summary: Publish booking-cancellation events.
      description: Published once a booking is cancelled, carrying the
        refund outcome.
      tags:
        - name: bookings
      externalDocs:
        description: Booking-cancellation event reference
        url: https://docs.example.com/events/booking-cancelled
      message:
        $ref: "#/components/messages/BookingCancelled"
components:
  messages:
    BookingConfirmed:
      name: BookingConfirmed
      title: Booking Confirmed
      contentType: application/json
      payload:
        $ref: "#/components/schemas/BookingConfirmedPayload"
      examples:
        - payload:
            booking_id: booking_af31
            guest_id: guest_456
            channel: email
    BookingCancelled:
      name: BookingCancelled
      title: Booking Cancelled
      contentType: application/json
      headers:
        $ref: "#/components/schemas/EventHeaders"
      payload:
        $ref: "#/components/schemas/BookingCancelledPayload"
      examples:
        - payload:
            booking_id: booking_af31
            reason: guest_requested
            refund:
              amount: 149.5
              currency: USD
  schemas:
    EventHeaders:
      type: object
      title: Event envelope headers
      description: Common envelope headers carried alongside a booking
        event's payload.
      required: [message_id, correlation_id]
      properties:
        message_id:
          type: string
          format: uuid
          description: Unique identifier for this message.
          example: 8f14e45f-ceea-467e-adc9-15d4f9d2b0dc
        correlation_id:
          type: string
          description: Identifier correlating this event with the request
            that triggered it.
          example: corr_9c21
    BookingConfirmedPayload:
      type: object
      title: BookingConfirmed payload
      required: [booking_id, guest_id, channel]
      properties:
        booking_id:
          type: string
          example: booking_af31
        guest_id:
          type: string
          example: guest_456
        channel:
          type: string
          example: email
    BookingCancelledPayload:
      type: object
      title: BookingCancelled payload
      required: [booking_id, reason]
      properties:
        booking_id:
          type: string
          example: booking_af31
        reason:
          type: string
          enum: [guest_requested, host_requested, payment_failed]
          example: guest_requested
        refund:
          $ref: "#/components/schemas/Refund"
    Refund:
      type: object
      title: Refund
      properties:
        amount:
          type: number
          format: double
          example: 149.5
        currency:
          type: string
          example: USD
"""

GROUPS = [
    {"name": "search-team", "title": "Search Team", "type": "team"},
    {"name": "booking-team", "title": "Booking Team", "type": "team"},
    {"name": "payments-team", "title": "Payments Team", "type": "team"},
    {"name": "listings-team", "title": "Listings Team", "type": "team"},
    {"name": "identity-team", "title": "Identity Team", "type": "team"},
    {
        "name": "notifications-team",
        "title": "Notifications Team",
        "type": "team",
    },
    {
        "name": "partner-integrations-team",
        "title": "Partner Integrations Team",
        "type": "team",
    },
]

SYSTEMS = [
    {
        # Owned by the unprivileged demo user's own Group (`seed_guest`), so a
        # visitor signed in as `guest` has one System they may edit.
        "name": "guest",
        "title": "Guest",
        "owner": "guest-team",
        "description": "Sandbox System owned by the public demo guest user.",
        "business_outcome": (
            "Lets a demo visitor try editing the catalog without touching "
            "anyone else's entities."
        ),
        "success_signal": "Visitors can create and edit entities here.",
        "planning_question": "What would you model in your own catalog?",
        "material_risk": "None: the demo resets nightly.",
    },
    {
        "name": "search-discovery",
        "title": "Search & Discovery",
        "owner": "search-team",
        "description": "Query, rank, and serve available listings to guests.",
        "business_outcome": (
            "Helps guests find a suitable stay quickly enough to begin "
            "checkout."
        ),
        "success_signal": (
            "Search-to-listing-view conversion and time to first useful result."
        ),
        "planning_question": (
            "Which ranking and inventory investments most improve qualified "
            "demand?"
        ),
        "material_risk": (
            "Stale availability or poor ranking sends demand to listings that "
            "cannot convert."
        ),
    },
    {
        "name": "booking-reservations",
        "title": "Booking & Reservations",
        "owner": "booking-team",
        "description": (
            "Owns the booking lifecycle: checkout, confirmation, cancellation."
        ),
        "business_outcome": (
            "Turns guest intent into a confirmed, policy-compliant reservation."
        ),
        "success_signal": (
            "Confirmed bookings, checkout conversion, and cancellation rate."
        ),
        "planning_question": (
            "Where does reservation friction or policy ambiguity cost "
            "completed bookings?"
        ),
        "material_risk": (
            "An inconsistent reservation state creates guest, host, and "
            "financial exposure."
        ),
        "documentation": (
            "Owns checkout, confirmation, and cancellation from a guest "
            "request through fulfilment."
        ),
    },
    {
        "name": "payments-payouts",
        "title": "Payments & Payouts",
        "owner": "payments-team",
        "description": "Charges guests and pays out hosts.",
        "business_outcome": (
            "Moves money accurately and predictably between guests, hosts, and "
            "partners."
        ),
        "success_signal": (
            "Payment authorization success, payout timeliness, and "
            "reconciliation exceptions."
        ),
        "planning_question": (
            "Which payment methods and payout routes improve coverage without "
            "increasing loss?"
        ),
        "material_risk": (
            "Incorrect or delayed money movement directly damages trust and "
            "regulatory posture."
        ),
    },
    {
        "name": "listings-supply",
        "title": "Listings & Supply",
        "owner": "listings-team",
        "description": (
            "Host-facing listing creation, pricing, and calendar management."
        ),
        "business_outcome": (
            "Grows reliable, bookable supply while helping hosts operate their "
            "inventory."
        ),
        "success_signal": (
            "Published active listings, calendar accuracy, and host completion "
            "rate."
        ),
        "planning_question": (
            "Which host workflows unlock quality supply in constrained markets?"
        ),
        "material_risk": (
            "Incomplete listing data or calendar drift reduces guest "
            "confidence and conversion."
        ),
    },
    {
        "name": "identity-trust",
        "title": "Identity & Trust",
        "owner": "identity-team",
        "description": "Accounts, auth, and post-stay reviews.",
        "business_outcome": (
            "Establishes the identity and trust signals needed for safe "
            "marketplace participation."
        ),
        "success_signal": (
            "Successful authentication, verification completion, and review "
            "participation."
        ),
        "planning_question": (
            "How can trust controls reduce abuse without adding avoidable "
            "onboarding friction?"
        ),
        "material_risk": (
            "Weak identity or trust controls expose guests, hosts, and the "
            "platform to abuse."
        ),
    },
    {
        "name": "notifications-messaging",
        "title": "Notifications & Messaging",
        "owner": "notifications-team",
        "description": "Email, push, and SMS delivery to guests and hosts.",
        "business_outcome": (
            "Keeps marketplace participants informed at the moments that "
            "affect their decisions."
        ),
        "success_signal": (
            "Delivery success, time-to-delivery, and engagement for "
            "transactional messages."
        ),
        "planning_question": (
            "Which messages improve completion and confidence without causing "
            "notification fatigue?"
        ),
        "material_risk": (
            "Late or missing transactional messages lead to missed stays, "
            "support contacts, and distrust."
        ),
    },
    {
        "name": "external-partners",
        "title": "External Partners",
        "owner": "partner-integrations-team",
        "description": "Third-party services the platform integrates with.",
        "tags": EXTERNAL,
        "business_outcome": (
            "Extends product coverage through specialized providers without "
            "owning their capabilities."
        ),
        "success_signal": (
            "Partner availability, integration error rate, and time to recover "
            "from provider incidents."
        ),
        "planning_question": (
            "Which provider dependencies require redundancy, renegotiation, or "
            "a product fallback?"
        ),
        "material_risk": (
            "A provider outage or contract change can interrupt a customer "
            "journey outside our control."
        ),
    },
]

RESOURCES = [
    {
        "name": "search-index",
        "title": "Search Index",
        "type": "cluster",
        "system": "search-discovery",
        "owner": "search-team",
        "description": (
            "Indexes listing attributes and availability signals for "
            "low-latency search."
        ),
    },
    {
        "name": "availability-cache",
        "title": "Availability Cache",
        "type": "cache",
        "system": "search-discovery",
        "owner": "search-team",
        "description": (
            "Caches short-lived availability responses to keep guest searches "
            "responsive."
        ),
    },
    {
        "name": "booking-db",
        "title": "Booking DB",
        "type": "database",
        "system": "booking-reservations",
        "owner": "booking-team",
        "description": (
            "Stores reservation state, guest and host commitments, and booking "
            "audit history."
        ),
        "documentation": (
            "Stores booking state and the audit trail for reservation changes."
        ),
    },
    {
        "name": "booking-events-queue",
        "title": "Booking Events Queue",
        "type": "queue",
        "system": "booking-reservations",
        "owner": "booking-team",
        "description": (
            "Carries booking lifecycle events to asynchronous consumers."
        ),
    },
    {
        "name": "payments-db",
        "title": "Payments DB",
        "type": "database",
        "system": "payments-payouts",
        "owner": "payments-team",
        "description": (
            "Stores payment attempts, authorization outcomes, and settlement "
            "state."
        ),
    },
    {
        "name": "ledger-db",
        "title": "Ledger DB",
        "type": "database",
        "system": "payments-payouts",
        "owner": "payments-team",
        "description": (
            "Records immutable financial entries used to reconcile host "
            "payouts."
        ),
    },
    {
        "name": "payout-events-queue",
        "title": "Payout Events Queue",
        "type": "queue",
        "system": "payments-payouts",
        "owner": "payments-team",
        "description": (
            "Distributes payout status changes to finance and notification "
            "consumers."
        ),
    },
    {
        "name": "listings-db",
        "title": "Listings DB",
        "type": "database",
        "system": "listings-supply",
        "owner": "listings-team",
        "description": (
            "Stores host-managed listing content, pricing rules, and calendars."
        ),
    },
    {
        "name": "media-bucket",
        "title": "Media Bucket",
        "type": "bucket",
        "system": "listings-supply",
        "owner": "listings-team",
        "description": (
            "Stores listing photos and other host-provided media assets."
        ),
    },
    {
        "name": "users-db",
        "title": "Users DB",
        "type": "database",
        "system": "identity-trust",
        "owner": "identity-team",
        "description": (
            "Stores account identity, authentication data, and trust-related "
            "profile state."
        ),
    },
    {
        "name": "notifications-queue",
        "title": "Notifications Queue",
        "type": "queue",
        "system": "notifications-messaging",
        "owner": "notifications-team",
        "description": (
            "Buffers transactional notification jobs for channel-specific "
            "delivery workers."
        ),
    },
]

# `DatabaseSchema` Facet DDL for each `type: 'database'` Resource above, so the
# Database Schema tab and ER Diagram have real tables/relations to render
# instead of being empty. `parsed_schema` is derived by the same
# `atlas_plugin_database_schema.parser.parse_schema()` the facet's own
# create/update endpoint calls (`api/views.py`'s `_apply_source`), not
# hand-written, so it can never drift from what the real parser produces for
# this `source_sql`. Every Resource without an entry here (queues, caches,
# buckets, the search cluster) simply has no `DatabaseSchema` row, same as
# today.
DATABASE_SCHEMAS = {
    "booking-db": """
CREATE TYPE booking_status AS ENUM
    ('pending', 'confirmed', 'cancelled', 'completed');

CREATE TABLE guests (
    id uuid PRIMARY KEY,
    email varchar(255) NOT NULL UNIQUE,
    full_name varchar(255) NOT NULL,
    created_at timestamp NOT NULL DEFAULT now()
);

CREATE TABLE bookings (
    id uuid PRIMARY KEY,
    guest_id uuid NOT NULL REFERENCES guests (id),
    listing_id uuid NOT NULL,
    status booking_status NOT NULL DEFAULT 'pending',
    check_in date NOT NULL,
    check_out date NOT NULL,
    guest_count integer NOT NULL DEFAULT 1,
    created_at timestamp NOT NULL DEFAULT now()
);

CREATE TABLE booking_events (
    id uuid PRIMARY KEY,
    booking_id uuid NOT NULL REFERENCES bookings (id),
    event_type varchar(64) NOT NULL,
    payload jsonb,
    created_at timestamp NOT NULL DEFAULT now()
);

CREATE INDEX idx_bookings_guest_id ON bookings (guest_id);
CREATE INDEX idx_booking_events_booking_id ON booking_events (booking_id);
""",
    "payments-db": """
CREATE TYPE payment_status AS ENUM
    ('pending', 'authorized', 'captured', 'failed', 'refunded');

CREATE TABLE payment_methods (
    id uuid PRIMARY KEY,
    guest_id uuid NOT NULL,
    provider varchar(64) NOT NULL,
    provider_token varchar(255) NOT NULL,
    created_at timestamp NOT NULL DEFAULT now()
);

CREATE TABLE payments (
    id uuid PRIMARY KEY,
    booking_id uuid NOT NULL,
    payment_method_id uuid NOT NULL REFERENCES payment_methods (id),
    status payment_status NOT NULL DEFAULT 'pending',
    amount numeric(10, 2) NOT NULL,
    currency varchar(3) NOT NULL DEFAULT 'USD',
    created_at timestamp NOT NULL DEFAULT now()
);

CREATE TABLE refunds (
    id uuid PRIMARY KEY,
    payment_id uuid NOT NULL REFERENCES payments (id),
    amount numeric(10, 2) NOT NULL,
    reason varchar(255),
    created_at timestamp NOT NULL DEFAULT now()
);

CREATE INDEX idx_payments_booking_id ON payments (booking_id);
""",
    "ledger-db": """
CREATE TYPE payout_status AS ENUM ('pending', 'processing', 'paid', 'failed');

CREATE TABLE hosts (
    id uuid PRIMARY KEY,
    email varchar(255) NOT NULL UNIQUE,
    payout_account varchar(255),
    created_at timestamp NOT NULL DEFAULT now()
);

CREATE TABLE ledger_entries (
    id uuid PRIMARY KEY,
    host_id uuid NOT NULL REFERENCES hosts (id),
    booking_id uuid NOT NULL,
    amount numeric(10, 2) NOT NULL,
    entry_type varchar(32) NOT NULL,
    created_at timestamp NOT NULL DEFAULT now()
);

CREATE TABLE payouts (
    id uuid PRIMARY KEY,
    host_id uuid NOT NULL REFERENCES hosts (id),
    status payout_status NOT NULL DEFAULT 'pending',
    amount numeric(10, 2) NOT NULL,
    tax_withheld numeric(10, 2) NOT NULL DEFAULT 0,
    paid_at timestamp,
    created_at timestamp NOT NULL DEFAULT now()
);

CREATE INDEX idx_ledger_entries_host_id ON ledger_entries (host_id);
CREATE INDEX idx_payouts_host_id ON payouts (host_id);
""",
    "listings-db": """
CREATE TYPE listing_status AS ENUM ('draft', 'active', 'paused', 'archived');

CREATE TABLE hosts (
    id uuid PRIMARY KEY,
    email varchar(255) NOT NULL UNIQUE,
    display_name varchar(255) NOT NULL
);

CREATE TABLE listings (
    id uuid PRIMARY KEY,
    host_id uuid NOT NULL REFERENCES hosts (id),
    title varchar(255) NOT NULL,
    status listing_status NOT NULL DEFAULT 'draft',
    base_price numeric(10, 2) NOT NULL,
    max_guests integer NOT NULL DEFAULT 1,
    created_at timestamp NOT NULL DEFAULT now()
);

CREATE TABLE listing_availability (
    id uuid PRIMARY KEY,
    listing_id uuid NOT NULL REFERENCES listings (id),
    date date NOT NULL,
    is_available boolean NOT NULL DEFAULT true,
    price_override numeric(10, 2)
);

CREATE UNIQUE INDEX idx_listing_availability_unique
    ON listing_availability (listing_id, date);
""",
    "users-db": """
CREATE TYPE account_role AS ENUM ('guest', 'host', 'admin');

CREATE TABLE accounts (
    id uuid PRIMARY KEY,
    email varchar(255) NOT NULL UNIQUE,
    role account_role NOT NULL DEFAULT 'guest',
    verified boolean NOT NULL DEFAULT false,
    created_at timestamp NOT NULL DEFAULT now()
);

CREATE TABLE sessions (
    id uuid PRIMARY KEY,
    account_id uuid NOT NULL REFERENCES accounts (id),
    token varchar(255) NOT NULL,
    expires_at timestamp NOT NULL,
    created_at timestamp NOT NULL DEFAULT now()
);

CREATE TABLE reviews (
    id uuid PRIMARY KEY,
    account_id uuid NOT NULL REFERENCES accounts (id),
    booking_id uuid NOT NULL,
    rating integer NOT NULL,
    comment text,
    created_at timestamp NOT NULL DEFAULT now()
);

CREATE INDEX idx_sessions_account_id ON sessions (account_id);
CREATE INDEX idx_reviews_account_id ON reviews (account_id);
""",
}

# (resource, singular, identifier, fields) — the same four args `openapi_spec()`
# turns into spec text below are reused by `_template_endpoints()` to build each
# API's `ApiEndpoint` docs, so the two can't drift apart (there is no
# OpenAPI importer here — this is single-sourced seed data, not
# parsing). `fields` are each resource's own properties beyond the generic
# `id`/`status`, resolved via `$ref` into `openapi_spec()`'s
# `components.schemas`. `booking-api` isn't here: its
# endpoints are hand-authored with richer content (below) instead of the generic
# list/create/get-by-id shape.
API_RESOURCE_SHAPES: dict[str, tuple[str, str, str, dict[str, dict]]] = {
    "search-api": (
        "searches",
        "search",
        "search",
        {
            "query": {
                "type": "string",
                "description": "Free-text search query.",
                "example": "apartment in Lisbon",
            },
            "location": {
                "type": "string",
                "description": "City or region the guest searched in.",
                "example": "Lisbon, Portugal",
            },
            "check_in": {
                "type": "string",
                "format": "date",
                "description": "Requested check-in date.",
                "example": "2026-03-01",
            },
            "check_out": {
                "type": "string",
                "format": "date",
                "description": "Requested check-out date.",
                "example": "2026-03-05",
            },
            "guest_count": {
                "type": "integer",
                "description": "Number of guests the search was scoped to.",
                "example": 2,
            },
        },
    ),
    "payments-api": (
        "payments",
        "payment",
        "payment",
        {
            "booking_id": {
                "type": "string",
                "description": "Booking this payment is collecting funds for.",
                "example": "booking_af31",
            },
            "amount": {
                "type": "number",
                "format": "double",
                "description": "Amount charged to the guest.",
                "example": 149.5,
            },
            "currency": {
                "type": "string",
                "description": "ISO 4217 currency code.",
                "example": "USD",
            },
            "method": {
                "type": "string",
                "description": "Payment method used.",
                "enum": ["card", "paypal", "bank_transfer"],
                "example": "card",
            },
        },
    ),
    "payout-api": (
        "payouts",
        "payout",
        "payout",
        {
            "host_id": {
                "type": "string",
                "description": "Host receiving the payout.",
                "example": "host_772c",
            },
            "amount": {
                "type": "number",
                "format": "double",
                "description": "Payout amount.",
                "example": 892.15,
            },
            "currency": {
                "type": "string",
                "description": "ISO 4217 currency code.",
                "example": "USD",
            },
            "destination": {
                "type": "string",
                "description": "Bank account or payout method identifier.",
                "example": "ba_1a2b3c",
            },
        },
    ),
    "listings-api": (
        "listings",
        "listing",
        "listing",
        {
            "title": {
                "type": "string",
                "description": "Listing headline shown to guests.",
                "example": "Sunny loft near the marina",
            },
            "city": {
                "type": "string",
                "description": "City the listing is located in.",
                "example": "Lisbon",
            },
            "country": {
                "type": "string",
                "description": "ISO 3166-1 alpha-2 country code.",
                "example": "PT",
            },
            "nightly_price": {
                "type": "number",
                "format": "double",
                "description": "Base nightly price.",
                "example": 118.0,
            },
            "currency": {
                "type": "string",
                "description": "ISO 4217 currency code.",
                "example": "EUR",
            },
            "max_guests": {
                "type": "integer",
                "description": (
                    "Maximum number of guests the listing accommodates."
                ),
                "example": 4,
            },
        },
    ),
    "reviews-api": (
        "reviews",
        "review",
        "review",
        {
            "booking_id": {
                "type": "string",
                "description": "Booking this review was written for.",
                "example": "booking_af31",
            },
            "author_id": {
                "type": "string",
                "description": "Guest or host who wrote the review.",
                "example": "guest_456",
            },
            "rating": {
                "type": "integer",
                "description": "Star rating from 1 to 5.",
                "example": 5,
            },
            "comment": {
                "type": "string",
                "description": "Free-text review comment.",
                "example": "Great stay, very clean and well located.",
            },
        },
    ),
    "stripe-api": (
        "payment-intents",
        "payment intent",
        "pi",
        {
            "amount": {
                "type": "integer",
                "description": (
                    "Amount to charge, in the smallest currency unit (cents)."
                ),
                "example": 14950,
            },
            "currency": {
                "type": "string",
                "description": "ISO 4217 currency code, lowercased.",
                "example": "usd",
            },
            "payment_method": {
                "type": "string",
                "description": "Stripe payment method identifier.",
                "example": "pm_1P2q3R4s5T6u",
            },
            "client_secret": {
                "type": "string",
                "description": (
                    "Secret used to confirm the payment intent client-side."
                ),
                "example": "pi_3P2q_secret_9x8y7z",
            },
        },
    ),
    "maps-api": (
        "geocodes",
        "geocode",
        "geo",
        {
            "address": {
                "type": "string",
                "description": "Address that was geocoded.",
                "example": "Praca do Comercio, Lisbon, Portugal",
            },
            "latitude": {
                "type": "number",
                "format": "double",
                "example": 38.7077,
            },
            "longitude": {
                "type": "number",
                "format": "double",
                "example": -9.1365,
            },
            "formatted_address": {
                "type": "string",
                "description": "Provider-normalized address.",
                "example": "Praca do Comercio, 1100-148 Lisboa, Portugal",
            },
        },
    ),
    "tax-api": (
        "tax-quotes",
        "tax quote",
        "tax",
        {
            "amount": {
                "type": "number",
                "format": "double",
                "description": (
                    "Payout amount the quote was calculated against."
                ),
                "example": 892.15,
            },
            "currency": {
                "type": "string",
                "description": "ISO 4217 currency code.",
                "example": "USD",
            },
            "jurisdiction": {
                "type": "string",
                "description": "Tax jurisdiction the quote applies to.",
                "example": "US-CA",
            },
            "tax_amount": {
                "type": "number",
                "format": "double",
                "description": (
                    "Withholding amount calculated for the jurisdiction."
                ),
                "example": 44.61,
            },
        },
    ),
    "twilio-sms-api": (
        "messages",
        "message",
        "message",
        {
            "to": {
                "type": "string",
                "description": "Recipient phone number, E.164 format.",
                "example": "+15551234567",
            },
            "from": {
                "type": "string",
                "description": "Sender phone number, E.164 format.",
                "example": "+15557654321",
            },
            "body": {
                "type": "string",
                "description": "SMS message body.",
                "example": "Your booking is confirmed!",
            },
        },
    ),
}

BOOKING_API_FIELDS: dict[str, dict] = {
    "listing_id": {
        "type": "string",
        "description": "The listing being booked.",
        "example": "listing_9f2a",
    },
    "check_in": {"type": "string", "format": "date", "example": "2026-03-01"},
    "check_out": {"type": "string", "format": "date", "example": "2026-03-05"},
    "guest_count": {"type": "integer", "example": 2},
}

APIS = [
    {
        "name": "search-api",
        "title": "Search API",
        "type": "openapi",
        "system": "search-discovery",
        "owner": "search-team",
        "description": (
            "Serves listing search and discovery results to guest-facing "
            "clients."
        ),
        "tags": ["Python", "Django", "REST"],
        "spec_content": openapi_spec(
            "Search API", *API_RESOURCE_SHAPES["search-api"]
        ),
    },
    {
        "name": "booking-api",
        "title": "Booking API",
        "type": "openapi",
        "system": "booking-reservations",
        "owner": "booking-team",
        "description": "Creates, confirms, and cancels guest reservations.",
        "tags": ["Python", "Django", "REST"],
        "documentation": (
            "Use this API to create, confirm, and cancel reservations."
        ),
        "spec_content": openapi_spec(
            "Booking API", "bookings", "booking", "booking", BOOKING_API_FIELDS
        ),
    },
    {
        "name": "payments-api",
        "title": "Payments API",
        "type": "openapi",
        "system": "payments-payouts",
        "owner": "payments-team",
        "description": "Initiates and tracks guest payment collection.",
        "tags": ["Python", "FastAPI", "REST"],
        "spec_content": openapi_spec(
            "Payments API", *API_RESOURCE_SHAPES["payments-api"]
        ),
    },
    {
        "name": "payout-api",
        "title": "Payout API",
        "type": "openapi",
        "system": "payments-payouts",
        "owner": "payments-team",
        "description": "Creates and tracks host payout instructions.",
        "tags": ["Python", "FastAPI", "REST"],
        "spec_content": openapi_spec(
            "Payout API", *API_RESOURCE_SHAPES["payout-api"]
        ),
    },
    {
        "name": "listings-api",
        "title": "Listings API",
        "type": "openapi",
        "system": "listings-supply",
        "owner": "listings-team",
        "description": "Manages host listings, pricing, and availability data.",
        "tags": ["Python", "Django", "REST"],
        "spec_content": openapi_spec(
            "Listings API", *API_RESOURCE_SHAPES["listings-api"]
        ),
    },
    {
        "name": "reviews-api",
        "title": "Reviews API",
        "type": "openapi",
        "system": "identity-trust",
        "owner": "identity-team",
        "description": (
            "Creates and retrieves post-stay guest and host reviews."
        ),
        "tags": ["Python", "Django", "REST"],
        "spec_content": openapi_spec(
            "Reviews API", *API_RESOURCE_SHAPES["reviews-api"]
        ),
    },
    {
        "name": "notifications-api",
        "title": "Notifications API",
        "type": "asyncapi",
        "system": "notifications-messaging",
        "owner": "notifications-team",
        "description": (
            "Publishes booking and payout events for notification delivery."
        ),
        "tags": ["Python", "Kafka", "AsyncAPI"],
        "spec_content": ASYNCAPI_SPEC,
    },
    {
        "name": "booking-events-api",
        "title": "Booking Events API",
        "type": "asyncapi",
        "system": "booking-reservations",
        "owner": "booking-team",
        "description": (
            "Publishes booking lifecycle events for downstream consumers."
        ),
        "tags": ["Python", "Kafka", "AsyncAPI"],
        "spec_content": BOOKING_EVENTS_ASYNCAPI_SPEC,
    },
    {
        "name": "stripe-api",
        "title": "Stripe API",
        "type": "openapi",
        "system": "external-partners",
        "owner": "partner-integrations-team",
        "description": (
            "External payment-provider contract for charges, refunds, and "
            "transfers."
        ),
        "tags": [*EXTERNAL, "REST"],
        "spec_content": openapi_spec(
            "Stripe API", *API_RESOURCE_SHAPES["stripe-api"]
        ),
    },
    {
        "name": "maps-api",
        "title": "Maps API",
        "type": "openapi",
        "system": "external-partners",
        "owner": "partner-integrations-team",
        "description": (
            "External geocoding contract used to validate listing addresses."
        ),
        "tags": [*EXTERNAL, "REST"],
        "spec_content": openapi_spec(
            "Maps API", *API_RESOURCE_SHAPES["maps-api"]
        ),
    },
    {
        "name": "tax-api",
        "title": "Tax & Compliance API",
        "type": "openapi",
        "system": "external-partners",
        "owner": "partner-integrations-team",
        "description": (
            "External tax calculation contract for payout withholding."
        ),
        "tags": [*EXTERNAL, "REST"],
        "spec_content": openapi_spec(
            "Tax & Compliance API", *API_RESOURCE_SHAPES["tax-api"]
        ),
    },
    {
        "name": "twilio-sms-api",
        "title": "Twilio SMS API",
        "type": "openapi",
        "system": "external-partners",
        "owner": "partner-integrations-team",
        "description": (
            "External SMS delivery contract for transactional messages."
        ),
        "tags": [*EXTERNAL, "REST"],
        "spec_content": openapi_spec(
            "Twilio SMS API", *API_RESOURCE_SHAPES["twilio-sms-api"]
        ),
    },
]

COMPONENTS = [
    {
        "name": "search-service",
        "title": "Search Service",
        "type": "service",
        "lifecycle": "production",
        "system": "search-discovery",
        "owner": "search-team",
        "description": (
            "Executes guest listing queries against the search index and "
            "availability cache."
        ),
        "provides_apis": ["search-api"],
        "depends_on": ["search-index", "availability-cache"],
        "tags": ["Python", "Django", "Elasticsearch", "Redis"],
    },
    {
        "name": "ranking-worker",
        "title": "Ranking Worker",
        "type": "worker",
        "lifecycle": "experimental",
        "system": "search-discovery",
        "owner": "search-team",
        "depends_on": ["search-index"],
        "description": "Computes ranking signals used to order search results.",
        "tags": ["Python", "Celery", "Machine Learning"],
    },
    {
        "name": "booking-service",
        "title": "Booking Service",
        "type": "service",
        "lifecycle": "production",
        "system": "booking-reservations",
        "owner": "booking-team",
        "description": (
            "Coordinates reservation state from availability checks through "
            "confirmation."
        ),
        "documentation": (
            "Coordinates reservation state and publishes booking events."
        ),
        "provides_apis": ["booking-api", "booking-events-api"],
        "consumes_apis": ["search-api", "payments-api", "listings-api"],
        "depends_on": ["booking-db", "booking-events-queue"],
        "tags": ["Python", "Django", "PostgreSQL", "Kafka"],
    },
    {
        "name": "booking-web",
        "title": "Booking Web",
        "type": "website",
        "lifecycle": "production",
        "system": "booking-reservations",
        "owner": "booking-team",
        "consumes_apis": ["booking-api", "search-api"],
        "description": (
            "Presents the guest search, checkout, and reservation-management "
            "experience."
        ),
        "tags": ["React", "TypeScript", "Vite"],
    },
    {
        "name": "cancellation-worker",
        "title": "Cancellation Worker",
        "type": "worker",
        "lifecycle": "production",
        "system": "booking-reservations",
        "owner": "booking-team",
        "description": (
            "Processes cancellation requests and coordinates applicable "
            "refunds."
        ),
        "consumes_apis": ["booking-api", "payments-api"],
        "depends_on": ["booking-events-queue"],
        "tags": ["Python", "Celery", "Kafka"],
    },
    {
        "name": "payment-service",
        "title": "Payment Service",
        "type": "service",
        "lifecycle": "production",
        "system": "payments-payouts",
        "owner": "payments-team",
        "description": (
            "Collects guest payments and records their processing outcome."
        ),
        "provides_apis": ["payments-api"],
        "consumes_apis": ["stripe-api"],
        "depends_on": ["payments-db"],
        "tags": ["Python", "FastAPI", "PostgreSQL", "Stripe"],
    },
    {
        "name": "payout-service",
        "title": "Payout Service",
        "type": "service",
        "lifecycle": "production",
        "system": "payments-payouts",
        "owner": "payments-team",
        "description": (
            "Calculates host earnings, tax withholding, and payout "
            "instructions."
        ),
        "provides_apis": ["payout-api"],
        "consumes_apis": ["stripe-api", "tax-api"],
        "depends_on": ["ledger-db", "payout-events-queue"],
        "tags": ["Python", "FastAPI", "PostgreSQL", "Stripe"],
    },
    {
        "name": "ledger-worker",
        "title": "Ledger Worker",
        "type": "worker",
        "lifecycle": "production",
        "system": "payments-payouts",
        "owner": "payments-team",
        "depends_on": ["ledger-db"],
        "description": (
            "Posts reconciled financial events to the payout ledger."
        ),
        "tags": ["Python", "Celery", "PostgreSQL"],
    },
    {
        "name": "listing-service",
        "title": "Listing Service",
        "type": "service",
        "lifecycle": "production",
        "system": "listings-supply",
        "owner": "listings-team",
        "description": (
            "Manages host listing content, calendars, and publication state."
        ),
        "provides_apis": ["listings-api"],
        "consumes_apis": ["maps-api"],
        "depends_on": ["listings-db", "media-bucket"],
        "tags": ["Python", "Django", "PostgreSQL", "S3"],
    },
    {
        "name": "pricing-engine",
        "title": "Pricing Engine",
        "type": "service",
        "lifecycle": "experimental",
        "system": "listings-supply",
        "owner": "listings-team",
        "consumes_apis": ["listings-api"],
        "description": "Recommends base pricing and rules for host listings.",
        "tags": ["Python", "FastAPI", "Machine Learning"],
    },
    {
        "name": "host-portal",
        "title": "Host Portal",
        "type": "website",
        "lifecycle": "production",
        "system": "listings-supply",
        "owner": "listings-team",
        "consumes_apis": ["listings-api"],
        "description": (
            "Provides hosts with listing, calendar, and pricing management "
            "tools."
        ),
        "tags": ["React", "TypeScript", "Vite"],
    },
    {
        "name": "auth-service",
        "title": "Auth Service",
        "type": "service",
        "lifecycle": "production",
        "system": "identity-trust",
        "owner": "identity-team",
        "depends_on": ["users-db"],
        "description": (
            "Authenticates users and manages account access credentials."
        ),
        "tags": ["Python", "Django", "OAuth 2.0", "PostgreSQL"],
    },
    {
        "name": "review-service",
        "title": "Review Service",
        "type": "service",
        "lifecycle": "production",
        "system": "identity-trust",
        "owner": "identity-team",
        "provides_apis": ["reviews-api"],
        "depends_on": ["users-db"],
        "description": (
            "Collects and serves post-stay reviews for marketplace trust."
        ),
        "tags": ["Python", "Django", "PostgreSQL"],
    },
    {
        "name": "notification-service",
        "title": "Notification Service",
        "type": "service",
        "lifecycle": "production",
        "system": "notifications-messaging",
        "owner": "notifications-team",
        "description": (
            "Routes transactional events to the appropriate delivery channel."
        ),
        "provides_apis": ["notifications-api"],
        "consumes_apis": ["twilio-sms-api"],
        "depends_on": ["notifications-queue"],
        "tags": ["Python", "FastAPI", "Kafka", "AsyncAPI"],
    },
    {
        "name": "email-worker",
        "title": "Email Worker",
        "type": "worker",
        "lifecycle": "production",
        "system": "notifications-messaging",
        "owner": "notifications-team",
        "depends_on": ["notifications-queue"],
        "description": (
            "Delivers queued transactional emails to guests and hosts."
        ),
        "tags": ["Python", "Celery", "SendGrid"],
    },
    {
        "name": "sms-worker",
        "title": "SMS Worker",
        "type": "worker",
        "lifecycle": "production",
        "system": "notifications-messaging",
        "owner": "notifications-team",
        "description": (
            "Delivers queued transactional SMS messages through Twilio."
        ),
        "consumes_apis": ["twilio-sms-api"],
        "depends_on": ["notifications-queue"],
        "tags": ["Python", "Celery", "Twilio"],
    },
    {
        "name": "stripe-gateway",
        "title": "Stripe Gateway",
        "type": "service",
        "lifecycle": "production",
        "system": "external-partners",
        "owner": "partner-integrations-team",
        "description": (
            "Represents the Stripe integration boundary used for payment "
            "operations."
        ),
        "provides_apis": ["stripe-api"],
        "tags": [*EXTERNAL, "Stripe", "REST"],
    },
    {
        "name": "maps-provider",
        "title": "Maps Provider",
        "type": "service",
        "lifecycle": "production",
        "system": "external-partners",
        "owner": "partner-integrations-team",
        "description": (
            "Represents the maps and geocoding provider integration boundary."
        ),
        "provides_apis": ["maps-api"],
        "tags": [*EXTERNAL, "Google Maps", "REST"],
    },
    {
        "name": "tax-compliance-provider",
        "title": "Tax Compliance Provider",
        "type": "service",
        "lifecycle": "production",
        "system": "external-partners",
        "owner": "partner-integrations-team",
        "description": (
            "Represents the external tax and compliance calculation boundary."
        ),
        "provides_apis": ["tax-api"],
        "tags": [*EXTERNAL, "REST"],
    },
    {
        "name": "sms-gateway-twilio",
        "title": "SMS Gateway (Twilio)",
        "type": "service",
        "lifecycle": "production",
        "system": "external-partners",
        "owner": "partner-integrations-team",
        "description": (
            "Represents the Twilio boundary used to send SMS messages."
        ),
        "provides_apis": ["twilio-sms-api"],
        "tags": [*EXTERNAL, "Twilio", "REST"],
    },
    # The four Services below widen the cast of consumers so that
    # `GET /listings/{id}` and the `booking.cancelled` channel are each used
    # by several Services of several teams — enough to show the dependency
    # graphs grouped by team or system (see `ENDPOINT_USAGES` and
    # `OPERATION_USAGES`).
    {
        "name": "booking-mobile-app",
        "title": "Booking Mobile App",
        "type": "website",
        "lifecycle": "production",
        "system": "booking-reservations",
        "owner": "booking-team",
        "consumes_apis": ["listings-api"],
        "description": (
            "Guest app for browsing listings, booking, and cancelling stays "
            "on a phone."
        ),
        "tags": ["React Native", "TypeScript"],
    },
    {
        "name": "trust-safety-service",
        "title": "Trust & Safety Service",
        "type": "service",
        "lifecycle": "production",
        "system": "identity-trust",
        "owner": "identity-team",
        "consumes_apis": ["listings-api"],
        "depends_on": ["users-db"],
        "description": (
            "Screens listings and bookings for fraud and policy violations."
        ),
        "tags": ["Python", "Django", "Machine Learning"],
    },
    {
        "name": "push-worker",
        "title": "Push Worker",
        "type": "worker",
        "lifecycle": "production",
        "system": "notifications-messaging",
        "owner": "notifications-team",
        "consumes_apis": ["listings-api"],
        "depends_on": ["notifications-queue"],
        "description": (
            "Delivers queued transactional push notifications to the mobile "
            "app."
        ),
        "tags": ["Python", "Celery"],
    },
    {
        "name": "channel-manager-sync",
        "title": "Channel Manager Sync",
        "type": "service",
        "lifecycle": "experimental",
        "system": "external-partners",
        "owner": "partner-integrations-team",
        "consumes_apis": ["listings-api"],
        "description": (
            "Mirrors listings and cancellations to partner booking channels."
        ),
        "tags": ["Python", "REST"],
    },
]

# Directed C4 interactions layered on top of the derived
# provides/consumes/depends-on structure above, covering each
# ArchitectureRelationship interaction kind plus a cross-boundary call to an
# External-tagged system.
ARCHITECTURE_RELATIONSHIPS = [
    {
        "source": "booking-service",
        "target_kind": "component",
        "target": "payment-service",
        "label": "Charges guest payment via",
        "technology": "REST/HTTPS",
        "interaction_kind": "synchronous",
        "tags": ["runtime"],
    },
    {
        "source": "booking-service",
        "target_kind": "resource",
        "target": "booking-events-queue",
        "label": "Publishes booking lifecycle events to",
        "technology": "Kafka",
        "interaction_kind": "asynchronous",
        "tags": ["events"],
    },
    {
        "source": "payment-service",
        "target_kind": "resource",
        "target": "payments-db",
        "label": "Reads and writes payment records in",
        "technology": "PostgreSQL",
        "interaction_kind": "data-access",
        "tags": ["runtime"],
    },
    {
        "source": "payment-service",
        "target_kind": "api",
        "target": "stripe-api",
        "label": "Processes guest charges through",
        "technology": "REST/HTTPS",
        "interaction_kind": "synchronous",
        "tags": ["integration"],
    },
    {
        "source": "payout-service",
        "target_kind": "api",
        "target": "tax-api",
        "label": "Requests payout tax withholding from",
        "technology": "REST/HTTPS",
        "interaction_kind": "synchronous",
        "tags": ["integration"],
    },
    {
        "source": "notification-service",
        "target_kind": "api",
        "target": "twilio-sms-api",
        "label": "Sends SMS notifications through",
        "technology": "REST/HTTPS",
        "interaction_kind": "synchronous",
        "tags": ["integration"],
    },
    {
        "source": "email-worker",
        "target_kind": "resource",
        "target": "notifications-queue",
        "label": "Consumes queued email jobs from",
        "technology": "Kafka",
        "interaction_kind": "asynchronous",
        "tags": ["events"],
    },
    {
        "source": "listing-service",
        "target_kind": "api",
        "target": "maps-api",
        "label": "Validates listing addresses via",
        "technology": "REST/HTTPS",
        "interaction_kind": "synchronous",
        "tags": ["integration"],
    },
]

# The guest is a catalog User acting as the outgoing source of a manual,
# human-triggered interaction, demonstrating that Architecture Relationship
# endpoints render as a C4 Person.
GUEST_ACTOR = {
    "name": "guest-persona",
    "display_name": "Guest",
    "email": "guest@demo.atlas.local",
}

ACTOR_ARCHITECTURE_RELATIONSHIPS = [
    {
        "target_kind": "component",
        "target": "booking-web",
        "label": "Searches and books a stay via",
        "technology": "Browser",
        "interaction_kind": "manual",
        "tags": ["runtime"],
    },
]

# `booking-api` gets real Endpoint
# documentation and Service links so the endpoint explorer has something to
# show without hand-seeding data. `GET /bookings/{id}` demonstrates a
# multi-consumer endpoint; linking
# `payment-service` to it below also demonstrates auto-`consumesAPI` creation,
# since `payment-service` doesn't otherwise consume `booking-api`.
ENDPOINTS = [
    {
        "api": "booking-api",
        "method": "POST",
        "path": "/bookings",
        "operation_id": "createBooking",
        "summary": "Create a booking",
        "description": (
            "Creates a pending reservation for a listing and date range; the "
            "guest is charged once payment is captured."
        ),
        "tags": ["bookings"],
        "request": {
            "body": {
                "content_type": "application/json",
                "schema": {
                    "type": "object",
                    "properties": {
                        "listing_id": {
                            "type": "string",
                            "description": "The listing being booked.",
                        },
                        "check_in": {"type": "string", "format": "date"},
                        "check_out": {"type": "string", "format": "date"},
                        "guest_count": {"type": "integer"},
                    },
                    "required": ["listing_id", "check_in", "check_out"],
                },
                "example": {
                    "listing_id": "listing_9f2a",
                    "check_in": "2026-03-01",
                    "check_out": "2026-03-05",
                    "guest_count": 2,
                },
            },
        },
        "responses": [
            {
                "status_code": "201",
                "description": "Booking created in a pending state.",
                "content_type": "application/json",
                "schema": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "status": {"type": "string", "enum": ["pending"]},
                    },
                },
                "example": {"id": "booking_af31", "status": "pending"},
            },
            {
                "status_code": "400",
                "description": (
                    "The listing is unavailable for the requested dates."
                ),
                "content_type": "application/json",
            },
        ],
    },
    {
        "api": "booking-api",
        "method": "GET",
        "path": "/bookings/{id}",
        "operation_id": "getBooking",
        "summary": "Get a booking by ID",
        "tags": ["bookings"],
        "request": {
            "parameters": [
                {
                    "name": "id",
                    "location": "path",
                    "required": True,
                    "description": "Booking ID",
                    "schema": {"type": "string"},
                },
            ],
        },
        "responses": [
            {
                "status_code": "200",
                "description": "The booking.",
                "content_type": "application/json",
                "schema": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "status": {"type": "string"},
                        "listing_id": {"type": "string"},
                        "check_in": {"type": "string", "format": "date"},
                        "check_out": {"type": "string", "format": "date"},
                    },
                },
                "example": {
                    "id": "booking_af31",
                    "status": "confirmed",
                    "listing_id": "listing_9f2a",
                    "check_in": "2026-03-01",
                    "check_out": "2026-03-05",
                },
            },
            {
                "status_code": "404",
                "description": "No booking exists with that ID.",
                "content_type": "application/json",
            },
        ],
    },
    {
        "api": "booking-api",
        "method": "POST",
        "path": "/bookings/{id}/cancel",
        "operation_id": "cancelBooking",
        "summary": "Cancel a booking",
        "deprecated": True,
        "tags": ["bookings"],
        "description": (
            "Cancels a booking and triggers an eligible refund. Deprecated in "
            "favor of `DELETE /bookings/{id}`."
        ),
        "request": {
            "parameters": [
                {
                    "name": "id",
                    "location": "path",
                    "required": True,
                    "description": "Booking ID",
                    "schema": {"type": "string"},
                },
            ],
            "body": {
                "content_type": "application/json",
                "schema": {
                    "type": "object",
                    "properties": {"reason": {"type": "string"}},
                },
                "example": {"reason": "guest_requested"},
            },
        },
        "responses": [
            {
                "status_code": "200",
                "description": "The booking was cancelled.",
                "content_type": "application/json",
                "schema": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "status": {"type": "string", "enum": ["cancelled"]},
                    },
                },
                "example": {"id": "booking_af31", "status": "cancelled"},
            },
            {
                "status_code": "404",
                "description": "No booking exists with that ID.",
                "content_type": "application/json",
            },
        ],
    },
    {
        # Soft-removed — kept to demo the
        # removed-endpoint warning banner against a real preserved
        # `ServiceEndpointUsage` link below.
        "api": "booking-api",
        "method": "DELETE",
        "path": "/bookings/{id}",
        "operation_id": "deleteBooking",
        "summary": "Delete a booking",
        "status": ApiEndpoint.STATUS_REMOVED,
        "tags": ["bookings"],
        "description": (
            "Superseded by `POST /bookings/{id}/cancel`, which preserves a "
            "cancellation record instead of deleting the booking outright."
        ),
        "request": {
            "parameters": [
                {
                    "name": "id",
                    "location": "path",
                    "required": True,
                    "description": "Booking ID",
                    "schema": {"type": "string"},
                },
            ],
        },
        "responses": [
            {
                "status_code": "204",
                "description": "The booking was deleted.",
                "content_type": "",
            },
        ],
    },
]

# Every other `openapi`-typed demo API gets the same generic
# list/create/get-by-id Endpoints its spec text already documents
# (`_template_endpoints`, built from `API_RESOURCE_SHAPES` — single-sourced, not
# parsed). `notifications-api` is `asyncapi`-typed (pub/sub channels, not HTTP
# method+path operations) and is intentionally not given `ApiEndpoint` rows.
for _api_name, _shape in API_RESOURCE_SHAPES.items():
    ENDPOINTS.extend(_template_endpoints(_api_name, *_shape))

ENDPOINT_USAGES = [
    {
        "api": "booking-api",
        "method": "POST",
        "path": "/bookings",
        "service": "booking-web",
    },
    {
        "api": "booking-api",
        "method": "GET",
        "path": "/bookings/{id}",
        "service": "booking-web",
    },
    {
        "api": "booking-api",
        "method": "GET",
        "path": "/bookings/{id}",
        "service": "cancellation-worker",
    },
    {
        "api": "booking-api",
        "method": "GET",
        "path": "/bookings/{id}",
        "service": "payment-service",
    },
    {
        "api": "booking-api",
        "method": "POST",
        "path": "/bookings/{id}/cancel",
        "service": "cancellation-worker",
    },
    # A legacy link to the removed DELETE endpoint, preserved on purpose
    # (removal never discards existing links).
    {
        "api": "booking-api",
        "method": "DELETE",
        "path": "/bookings/{id}",
        "service": "cancellation-worker",
    },
    # Links below mirror each Component's existing `consumes_apis` (COMPONENTS
    # above) at the endpoint level, so several of these are genuine multiple-
    # services-on-one-endpoint cases: `GET /listings/{id}` has 3 consumers
    # (booking-service, pricing-engine, host-portal), matching `listings-api`'s
    # 3 API-level consumers already declared there.
    {
        "api": "search-api",
        "method": "GET",
        "path": "/searches",
        "service": "booking-service",
    },
    {
        "api": "search-api",
        "method": "GET",
        "path": "/searches",
        "service": "booking-web",
    },
    {
        "api": "payments-api",
        "method": "GET",
        "path": "/payments/{id}",
        "service": "booking-service",
    },
    {
        "api": "payments-api",
        "method": "GET",
        "path": "/payments/{id}",
        "service": "cancellation-worker",
    },
    {
        "api": "listings-api",
        "method": "GET",
        "path": "/listings/{id}",
        "service": "booking-service",
    },
    {
        "api": "listings-api",
        "method": "GET",
        "path": "/listings/{id}",
        "service": "pricing-engine",
    },
    {
        "api": "listings-api",
        "method": "GET",
        "path": "/listings/{id}",
        "service": "host-portal",
    },
    {
        "api": "stripe-api",
        "method": "POST",
        "path": "/payment-intents",
        "service": "payment-service",
    },
    {
        "api": "stripe-api",
        "method": "POST",
        "path": "/payment-intents",
        "service": "payout-service",
    },
    {
        "api": "maps-api",
        "method": "POST",
        "path": "/geocodes",
        "service": "listing-service",
    },
    {
        "api": "tax-api",
        "method": "POST",
        "path": "/tax-quotes",
        "service": "payout-service",
    },
    {
        "api": "twilio-sms-api",
        "method": "POST",
        "path": "/messages",
        "service": "notification-service",
    },
    {
        "api": "twilio-sms-api",
        "method": "POST",
        "path": "/messages",
        "service": "sms-worker",
    },
    # Listing details are needed all over the platform: with the three links
    # above, `GET /listings/{id}` has 16 consumers from six teams, which shows
    # the consumers graph grouped by team or system.
    {
        "api": "listings-api",
        "method": "GET",
        "path": "/listings/{id}",
        "service": "booking-web",
    },
    {
        "api": "listings-api",
        "method": "GET",
        "path": "/listings/{id}",
        "service": "booking-mobile-app",
    },
    {
        "api": "listings-api",
        "method": "GET",
        "path": "/listings/{id}",
        "service": "cancellation-worker",
    },
    {
        "api": "listings-api",
        "method": "GET",
        "path": "/listings/{id}",
        "service": "search-service",
    },
    {
        "api": "listings-api",
        "method": "GET",
        "path": "/listings/{id}",
        "service": "ranking-worker",
    },
    {
        "api": "listings-api",
        "method": "GET",
        "path": "/listings/{id}",
        "service": "payment-service",
    },
    {
        "api": "listings-api",
        "method": "GET",
        "path": "/listings/{id}",
        "service": "payout-service",
    },
    {
        "api": "listings-api",
        "method": "GET",
        "path": "/listings/{id}",
        "service": "review-service",
    },
    {
        "api": "listings-api",
        "method": "GET",
        "path": "/listings/{id}",
        "service": "trust-safety-service",
    },
    {
        "api": "listings-api",
        "method": "GET",
        "path": "/listings/{id}",
        "service": "notification-service",
    },
    {
        "api": "listings-api",
        "method": "GET",
        "path": "/listings/{id}",
        "service": "email-worker",
    },
    {
        "api": "listings-api",
        "method": "GET",
        "path": "/listings/{id}",
        "service": "push-worker",
    },
    {
        "api": "listings-api",
        "method": "GET",
        "path": "/listings/{id}",
        "service": "channel-manager-sync",
    },
    # `payout-api` and `reviews-api` are left with no links, so the demo also
    # shows the empty-consumers-graph state.
]

OPERATION_USAGES = [
    # The document owner of each operation's own API (`notification-service` for
    # `notifications-api`, `booking-service` for `booking-events-api`) is never
    # linked here — its role is implied from `direction` at read time
    # These rows are the *other* Services a human has
    # manually asserted a role for.
    {
        "api": "notifications-api",
        "operation_key": "payout.completed-receive",
        "service": "payout-service",
        "role": ServiceOperationUsage.ROLE_PUBLISHER,
    },
    # Two subscribers holding the *same* role on one operation —
    # the "at least one multi-subscriber-same-role case".
    {
        "api": "notifications-api",
        "operation_key": "notification.delivery-status-send",
        "service": "booking-service",
        "role": ServiceOperationUsage.ROLE_SUBSCRIBER,
    },
    {
        "api": "notifications-api",
        "operation_key": "notification.delivery-status-send",
        "service": "payout-service",
        "role": ServiceOperationUsage.ROLE_SUBSCRIBER,
    },
    # `booking.cancelled` is published by `booking-service` (the document owner,
    # implied) together with other Services of its team and of the listings
    # and partner teams, and consumed by Services of five teams — publishers and
    # subscribers both group by team. `listing-service` holds both roles.
    {
        "api": "booking-events-api",
        "operation_key": "booking.cancelled-send",
        "service": "cancellation-worker",
        "role": ServiceOperationUsage.ROLE_PUBLISHER,
    },
    {
        "api": "booking-events-api",
        "operation_key": "booking.cancelled-send",
        "service": "booking-mobile-app",
        "role": ServiceOperationUsage.ROLE_PUBLISHER,
    },
    {
        "api": "booking-events-api",
        "operation_key": "booking.cancelled-send",
        "service": "host-portal",
        "role": ServiceOperationUsage.ROLE_PUBLISHER,
    },
    {
        "api": "booking-events-api",
        "operation_key": "booking.cancelled-send",
        "service": "listing-service",
        "role": ServiceOperationUsage.ROLE_PUBLISHER,
    },
    {
        "api": "booking-events-api",
        "operation_key": "booking.cancelled-send",
        "service": "channel-manager-sync",
        "role": ServiceOperationUsage.ROLE_PUBLISHER,
    },
    {
        "api": "booking-events-api",
        "operation_key": "booking.cancelled-send",
        "service": "payment-service",
        "role": ServiceOperationUsage.ROLE_SUBSCRIBER,
    },
    {
        "api": "booking-events-api",
        "operation_key": "booking.cancelled-send",
        "service": "payout-service",
        "role": ServiceOperationUsage.ROLE_SUBSCRIBER,
    },
    {
        "api": "booking-events-api",
        "operation_key": "booking.cancelled-send",
        "service": "ledger-worker",
        "role": ServiceOperationUsage.ROLE_SUBSCRIBER,
    },
    {
        "api": "booking-events-api",
        "operation_key": "booking.cancelled-send",
        "service": "notification-service",
        "role": ServiceOperationUsage.ROLE_SUBSCRIBER,
    },
    {
        "api": "booking-events-api",
        "operation_key": "booking.cancelled-send",
        "service": "email-worker",
        "role": ServiceOperationUsage.ROLE_SUBSCRIBER,
    },
    {
        "api": "booking-events-api",
        "operation_key": "booking.cancelled-send",
        "service": "sms-worker",
        "role": ServiceOperationUsage.ROLE_SUBSCRIBER,
    },
    {
        "api": "booking-events-api",
        "operation_key": "booking.cancelled-send",
        "service": "push-worker",
        "role": ServiceOperationUsage.ROLE_SUBSCRIBER,
    },
    {
        "api": "booking-events-api",
        "operation_key": "booking.cancelled-send",
        "service": "pricing-engine",
        "role": ServiceOperationUsage.ROLE_SUBSCRIBER,
    },
    {
        "api": "booking-events-api",
        "operation_key": "booking.cancelled-send",
        "service": "listing-service",
        "role": ServiceOperationUsage.ROLE_SUBSCRIBER,
    },
    {
        "api": "booking-events-api",
        "operation_key": "booking.cancelled-send",
        "service": "review-service",
        "role": ServiceOperationUsage.ROLE_SUBSCRIBER,
    },
    {
        "api": "booking-events-api",
        "operation_key": "booking.cancelled-send",
        "service": "trust-safety-service",
        "role": ServiceOperationUsage.ROLE_SUBSCRIBER,
    },
    {
        "api": "booking-events-api",
        "operation_key": "booking.cancelled-send",
        "service": "ranking-worker",
        "role": ServiceOperationUsage.ROLE_SUBSCRIBER,
    },
]


# FLOWS steps below use two shorthand keys instead of hand-authoring
# `query_ref`/`event_ref` snapshots directly: `'query': (api, method, path)` and
# `'event': (api, operation_key)`. `_resolve_flow_step` expands each into the
# real snapshot the flows plugin expects, single- sourced from the
# `ApiEndpoint`/`ApiOperation` rows `_create_endpoints`/`_lookup_operations`
# already produced, so a seeded Query/Event step's `endpoint`/`operation` id can
# never drift from what was actually created.
def _resolve_flow_step(
    step: dict,
    apis: dict[str, CatalogEntity],
    endpoints: dict[tuple[str, str, str], ApiEndpoint],
    operations: dict[tuple[str, str], ApiOperation],
) -> dict:
    step = dict(step)
    if "query" in step:
        api_name, method, path = step.pop("query")
        endpoint = endpoints[(api_name, method, path)]
        step["query_ref"] = {
            "api": apis[api_name].ref,
            "endpoint": str(endpoint.id),
            "method": endpoint.method,
            "path": endpoint.path,
            # Snapshotted alongside method/path;
            # feeds the Call node's card subtitle.
            "summary": endpoint.summary,
        }
    if "event" in step:
        api_name, operation_key = step.pop("event")
        operation = operations[(api_name, operation_key)]
        step["event_ref"] = {
            "api": apis[api_name].ref,
            "operation": str(operation.id),
            "direction": operation.direction,
            "channel": operation.channel_address,
            "summary": operation.summary,
        }
    return step


FLOWS = [
    {
        "system": "search-discovery",
        "name": "search-flow",
        "title": "Search",
        "description": "A guest searches for available listings.",
        "steps": [
            {
                "id": "s1",
                "entity_ref": "component:booking-web",
                "next_step": {"id": "s2"},
            },
            {
                "id": "s2",
                "entity_ref": "api:search-api",
                "next_step": {"id": "s3"},
            },
            {
                "id": "s3",
                "entity_ref": "resource:availability-cache",
                "next_steps": [
                    {"id": "s4", "label": "cache hit"},
                    {"id": "s5", "label": "cache miss"},
                ],
            },
            # Cache hit skips straight to rendering results
            # (reconverges with the cache-miss
            # path's s6 at the shared s7 "show results" step).
            {
                "id": "s4",
                "entity_ref": "component:search-service",
                "next_step": {"id": "s7"},
            },
            {
                "id": "s5",
                "entity_ref": "resource:search-index",
                "next_step": {"id": "s6"},
            },
            {
                "id": "s6",
                "entity_ref": "component:ranking-worker",
                "next_step": {"id": "s7"},
            },
            {"id": "s7", "entity_ref": "component:booking-web"},
        ],
    },
    {
        "system": "booking-reservations",
        "name": "booking-flow",
        "title": "Booking",
        "description": "A guest books a listing and payment is captured.",
        "documentation": (
            "The flow reserves inventory, captures payment, then notifies the "
            "guest and host."
        ),
        "steps": [
            # No `title`/`summary` on these entity-backed steps
            # an
            # entity-backed step's card always renders the referenced entity's
            # own live `title`/`description` (see COMPONENTS/RESOURCES/APIS
            # above), never anything stored on the step itself; carrying both is
            # now rejected on save.
            {
                "id": "s1",
                "entity_ref": "component:booking-web",
                "next_step": {"id": "s2"},
            },
            {
                "id": "s2",
                "entity_ref": "component:booking-service",
                "next_steps": [
                    {"id": "s3", "label": "available"},
                    {"id": "s7", "label": "unavailable"},
                ],
            },
            {
                "id": "s3",
                "entity_ref": "resource:booking-db",
                "next_step": {"id": "s4"},
            },
            {
                "id": "s4",
                "entity_ref": "component:payment-service",
                "next_step": {"id": "s5"},
            },
            {
                "id": "s5",
                "entity_ref": "api:stripe-api",
                "next_step": {"id": "s6"},
            },
            {
                "id": "s6",
                "entity_ref": "resource:booking-events-queue",
                "next_step": {"id": "s8"},
            },
            {"id": "s7", "entity_ref": "component:notification-service"},
            {
                "id": "s8",
                "entity_ref": "component:notification-service",
                "next_step": {"id": "s9"},
            },
            {"id": "s9", "entity_ref": "component:listing-service"},
        ],
    },
    {
        "system": "booking-reservations",
        "name": "cancellation-flow",
        "title": "Cancellation",
        "description": "A guest cancels a booking, with or without a refund.",
        "steps": [
            {
                "id": "s1",
                "entity_ref": "component:booking-web",
                "next_step": {"id": "s2"},
            },
            {
                "id": "s2",
                "entity_ref": "component:booking-service",
                "next_steps": [
                    {"id": "s2b", "label": "refund eligible"},
                    {"id": "s6", "label": "no refund"},
                ],
            },
            {
                "id": "s2b",
                "entity_ref": "component:cancellation-worker",
                "next_step": {"id": "s3"},
            },
            {
                "id": "s3",
                "entity_ref": "component:payment-service",
                "next_step": {"id": "s4"},
            },
            {
                "id": "s4",
                "entity_ref": "api:stripe-api",
                "next_step": {"id": "s5"},
            },
            # Both the refund and no-refund branches notify the guest through
            # this same step (s5 is targeted by
            # both s4 and s6).
            {"id": "s5", "entity_ref": "component:notification-service"},
            {
                "id": "s6",
                "entity_ref": "resource:booking-db",
                "next_step": {"id": "s5"},
            },
        ],
    },
    {
        "system": "payments-payouts",
        "name": "payout-flow",
        "title": "Payout",
        "description": "A completed stay's earnings are paid out to the host.",
        "steps": [
            {
                "id": "s1",
                "entity_ref": "component:booking-service",
                "next_step": {"id": "s2"},
            },
            {
                "id": "s2",
                "entity_ref": "component:payout-service",
                "next_step": {"id": "s2b"},
            },
            {
                "id": "s2b",
                "entity_ref": "component:ledger-worker",
                "next_step": {"id": "s3"},
            },
            {
                "id": "s3",
                "entity_ref": "resource:ledger-db",
                "next_step": {"id": "s4"},
            },
            {
                "id": "s4",
                "entity_ref": "component:tax-compliance-provider",
                "next_step": {"id": "s5"},
            },
            {
                "id": "s5",
                "entity_ref": "api:stripe-api",
                "next_step": {"id": "s6"},
            },
            {
                "id": "s6",
                "entity_ref": "resource:payout-events-queue",
                "next_step": {"id": "s7"},
            },
            {"id": "s7", "entity_ref": "component:notification-service"},
        ],
    },
    {
        "system": "listings-supply",
        "name": "listing-publish-flow",
        "title": "Listing Publish",
        "description": (
            "A host publishes a new listing, which becomes searchable."
        ),
        "steps": [
            {
                "id": "s1",
                "entity_ref": "component:host-portal",
                "next_step": {"id": "s2"},
            },
            {
                "id": "s2",
                "entity_ref": "component:maps-provider",
                "next_step": {"id": "s3"},
            },
            {
                "id": "s3",
                "entity_ref": "component:pricing-engine",
                "next_step": {"id": "s4"},
            },
            {
                "id": "s4",
                "entity_ref": "resource:listings-db",
                "next_steps": [
                    {"id": "s5", "label": "photos attached"},
                    {"id": "s7", "label": "no photos"},
                ],
            },
            {
                "id": "s5",
                "entity_ref": "resource:media-bucket",
                "next_step": {"id": "s6"},
            },
            {"id": "s6", "entity_ref": "component:search-service"},
            {"id": "s7", "entity_ref": "component:notification-service"},
        ],
    },
    {
        "system": "identity-trust",
        "name": "signup-verification-flow",
        "title": "Signup & Verification",
        "description": (
            "A guest signs up, verifies their identity, and is approved to "
            "book or host."
        ),
        "steps": [
            {
                "id": "s1",
                "entity_ref": "user:guest-persona",
                "next_step": {"id": "s2"},
            },
            {
                "id": "s2",
                "entity_ref": "component:auth-service",
                "next_steps": [
                    {"id": "s3", "label": "manual verification required"},
                    {"id": "s6", "label": "auto-approved"},
                ],
            },
            {
                "id": "s3",
                "title": "Run identity document check",
                "external_label": "ID Verification Provider (KYC)",
                "next_step": {"id": "s4"},
            },
            {
                "id": "s4",
                "title": "Flag for manual review",
                "label_theme": "warning",
                "next_step": {"id": "s5"},
            },
            {"id": "s5", "entity_ref": "group:identity-team"},
            {
                "id": "s6",
                "entity_ref": "resource:users-db",
                "next_step": {"id": "s7"},
            },
            {
                "id": "s7",
                "entity_ref": "component:review-service",
                "next_step": {"id": "s8"},
            },
            {
                "id": "s8",
                "query": ("reviews-api", "GET", "/reviews"),
                "next_step": {"id": "s9"},
            },
            {"id": "s9", "entity_ref": "system:notifications-messaging"},
        ],
    },
    {
        "system": "notifications-messaging",
        "name": "notification-delivery-flow",
        "title": "Notification Delivery",
        "description": (
            "A booking-confirmed event fans out to email and SMS delivery, "
            "with a status report published back."
        ),
        "steps": [
            # No `title`/`summary` on any step here
            # Query/Event steps (s1, s6, s8) render text derived from their
            # picked Endpoint/Operation snapshot itself (method+path or
            # channel+direction, plus the owning API's raw name), the same as
            # entity-backed steps render from their live entity data; carrying a
            # stored title/summary alongside any of entity_ref/query_ref/
            # event_ref is now rejected on save.
            {
                "id": "s1",
                "event": ("booking-events-api", "booking.confirmed-send"),
                "next_step": {"id": "s2"},
            },
            {
                "id": "s2",
                "entity_ref": "component:notification-service",
                "next_steps": [
                    {"id": "s3", "label": "email channel"},
                    {"id": "s5", "label": "sms channel"},
                ],
            },
            {
                "id": "s3",
                "entity_ref": "component:email-worker",
                "next_step": {"id": "s4"},
            },
            # Both channels report delivery status back through the same s8
            # event step (s8 is targeted by both
            # s4 and s7).
            {
                "id": "s4",
                "title": "Delivers to the guest's inbox",
                "external_label": "SendGrid",
                "next_step": {"id": "s8"},
            },
            {
                "id": "s5",
                "entity_ref": "component:sms-worker",
                "next_step": {"id": "s6"},
            },
            {
                "id": "s6",
                "query": ("twilio-sms-api", "POST", "/messages"),
                "next_step": {"id": "s7"},
            },
            {
                "id": "s7",
                "entity_ref": "component:sms-gateway-twilio",
                "next_step": {"id": "s8"},
            },
            {
                "id": "s8",
                "event": (
                    "notifications-api",
                    "notification.delivery-status-send",
                ),
            },
        ],
    },
    {
        "system": "external-partners",
        "name": "payment-provider-incident-flow",
        "title": "Payment Provider Incident",
        "description": (
            "Stripe reports a failed charge; the platform reconciles and "
            "notifies the guest."
        ),
        "steps": [
            {
                "id": "s1",
                "entity_ref": "component:stripe-gateway",
                "next_step": {"id": "s2"},
            },
            {
                "id": "s2",
                "title": "Payment failed",
                "label_theme": "danger",
                "next_steps": [
                    {"id": "s3", "label": "retry succeeds"},
                    {"id": "s4", "label": "retry exhausted"},
                ],
            },
            {"id": "s3", "entity_ref": "resource:payments-db"},
            {
                "id": "s4",
                "entity_ref": "component:booking-service",
                "next_step": {"id": "s5"},
            },
            {"id": "s5", "entity_ref": "group:payments-team"},
        ],
    },
]


class Command(BaseCommand):
    help = (
        "Wipe the database and repopulate it with a booking-platform demo "
        "catalog."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--yes", action="store_true", help="Skip the confirmation prompt."
        )

    def handle(self, *args, **options) -> None:
        if not options["yes"]:
            answer = input(
                "This will WIPE the database and repopulate it with "
                "booking-platform demo data.\n"
                "Type 'yes' to continue: ",
            )
            if answer != "yes":
                self.stdout.write("Aborted.")
                return

        self.stdout.write("Flushing database...")
        call_command("flush", interactive=False)
        from atlas_plugin_standard_catalog.management.commands import (
            seed_admin,
            seed_guest,
        )

        seed_admin.bootstrap_administrator(
            username=os.environ.get("ATLAS_DEMO_ADMIN_USERNAME", "admin"),
            password=os.environ.get(
                "ATLAS_DEMO_ADMIN_PASSWORD", "atlas-demo-admin-password"
            ),
            email=os.environ.get("ATLAS_DEMO_ADMIN_EMAIL", "admin@example.com"),
            group="platform",
        )
        seed_guest.bootstrap_guest(
            username=os.environ.get("ATLAS_DEMO_GUEST_USERNAME", "guest"),
            password=os.environ.get(
                "ATLAS_DEMO_GUEST_PASSWORD", "atlas-demo-guest-password"
            ),
            email=os.environ.get("ATLAS_DEMO_GUEST_EMAIL", "guest@example.com"),
            group="guest-team",
        )

        with transaction.atomic():
            groups = self._create_groups()
            groups["guest-team"] = CatalogEntity.objects.get(
                kind=KIND_GROUP, name="guest-team"
            )
            systems = self._create_systems(groups)
            resources = self._create_resources(systems, groups)
            self._create_database_schemas(resources)
            apis = self._create_apis(systems, groups)
            components = self._create_components(
                systems, groups, apis, resources
            )
            endpoints = self._create_endpoints(apis)
            self._create_endpoint_usages(endpoints, components, apis)
            operations = self._lookup_operations(apis)
            self._create_operation_usages(operations, components)
            guest = self._create_guest_actor()
            self._create_architecture_relationships(
                components, apis, resources, guest
            )
            self._create_flows(systems, apis, endpoints, operations)
            self._color_tags()

        relationship_count = len(ARCHITECTURE_RELATIONSHIPS) + len(
            ACTOR_ARCHITECTURE_RELATIONSHIPS
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(GROUPS)} groups, "
                f"{len(SYSTEMS)} systems, {len(RESOURCES)} resources, "
                f"{len(DATABASE_SCHEMAS)} database schemas, "
                f"{len(APIS)} apis, "
                f"{len(COMPONENTS)} components, {len(ENDPOINTS)} endpoints, "
                f"{len(ENDPOINT_USAGES)} endpoint-service links, "
                f"{len(operations)} operations, "
                f"{len(OPERATION_USAGES)} operation-service links, "
                f"{len(FLOWS)} flows, "
                f"{relationship_count} architecture relationships.",
            )
        )

    def _create_groups(self) -> dict[str, CatalogEntity]:
        groups = {}
        for spec in GROUPS:
            entity = CatalogEntity.objects.create(
                kind=KIND_GROUP,
                name=spec["name"],
                title=spec["title"],
            )
            GroupDetails.objects.create(entity=entity, type=spec["type"])
            groups[spec["name"]] = entity
        self.stdout.write(f"Created {len(groups)} groups")
        return groups

    def _create_systems(
        self, groups: dict[str, CatalogEntity]
    ) -> dict[str, CatalogEntity]:
        systems = {}
        for spec in SYSTEMS:
            tags = spec.get("tags", [])
            entity = CatalogEntity.objects.create(
                kind=KIND_SYSTEM,
                name=spec["name"],
                title=spec["title"],
                description=spec["description"],
                documentation=documentation_for("system", spec),
                owner=groups[spec["owner"]],
                tags=tags,
            )
            SystemDetails.objects.create(entity=entity)
            ensure_tags_exist(tags)
            systems[spec["name"]] = entity
        self.stdout.write(f"Created {len(systems)} systems")
        return systems

    def _create_resources(
        self,
        systems: dict[str, CatalogEntity],
        groups: dict[str, CatalogEntity],
    ) -> dict[str, CatalogEntity]:
        resources = {}
        for spec in RESOURCES:
            entity = CatalogEntity.objects.create(
                kind=KIND_RESOURCE,
                name=spec["name"],
                title=spec["title"],
                owner=groups[spec["owner"]],
                description=spec["description"],
                documentation=documentation_for("resource", spec),
            )
            ResourceDetails.objects.create(
                entity=entity,
                type=spec["type"],
                system=systems[spec["system"]],
            )
            resources[spec["name"]] = entity
        self.stdout.write(f"Created {len(resources)} resources")
        return resources

    def _create_database_schemas(
        self, resources: dict[str, CatalogEntity]
    ) -> None:
        for name, sql in DATABASE_SCHEMAS.items():
            DatabaseSchema.objects.create(
                entity=resources[name],
                dialect=DatabaseSchema.DIALECT_POSTGRESQL,
                source_sql=sql,
                parsed_schema=parse_schema(
                    sql, dialect=DatabaseSchema.DIALECT_POSTGRESQL
                ),
                parse_status=DatabaseSchema.PARSE_STATUS_OK,
            )
        self.stdout.write(f"Created {len(DATABASE_SCHEMAS)} database schemas")

    def _create_apis(
        self,
        systems: dict[str, CatalogEntity],
        groups: dict[str, CatalogEntity],
    ) -> dict[str, CatalogEntity]:
        apis = {}
        for spec in APIS:
            tags = spec.get("tags", [])
            entity = CatalogEntity.objects.create(
                kind=KIND_API,
                name=spec["name"],
                title=spec["title"],
                owner=groups[spec["owner"]],
                tags=tags,
                description=spec["description"],
                documentation=documentation_for("api", spec),
            )
            ApiDetails.objects.create(
                entity=entity,
                type=spec["type"],
                system=systems[spec["system"]],
                spec_source=ApiDetails.SPEC_SOURCE_INLINE,
                spec_content=spec["spec_content"],
            )
            ensure_tags_exist(tags)
            apis[spec["name"]] = entity
        self.stdout.write(f"Created {len(apis)} apis")
        return apis

    def _create_components(
        self,
        systems: dict[str, CatalogEntity],
        groups: dict[str, CatalogEntity],
        apis: dict[str, CatalogEntity],
        resources: dict[str, CatalogEntity],
    ) -> dict[str, CatalogEntity]:
        components = {}
        for spec in COMPONENTS:
            tags = spec.get("tags", [])
            entity = CatalogEntity.objects.create(
                kind=KIND_COMPONENT,
                name=spec["name"],
                title=spec["title"],
                owner=groups[spec["owner"]],
                tags=tags,
                description=spec["description"],
                documentation=documentation_for("component", spec),
            )
            details = ComponentDetails.objects.create(
                entity=entity,
                type=spec["type"],
                lifecycle=spec["lifecycle"],
                system=systems[spec["system"]],
            )
            ensure_tags_exist(tags)
            details.provides_apis.set(
                apis[ref] for ref in spec.get("provides_apis", [])
            )
            details.consumes_apis.set(
                apis[ref] for ref in spec.get("consumes_apis", [])
            )
            details.depends_on.set(
                resources[ref] for ref in spec.get("depends_on", [])
            )
            components[spec["name"]] = entity
        self.stdout.write(f"Created {len(COMPONENTS)} components")
        return components

    def _create_endpoints(
        self, apis: dict[str, CatalogEntity]
    ) -> dict[tuple[str, str, str], ApiEndpoint]:
        # `update_or_create`, not `create`: `_create_apis` already triggered
        # `atlas_plugin_apis.openapi_import.sync_endpoints_from_spec` (via
        # `ApiDetails`'s `post_save` signal) for every openapi-typed API above,
        # which may have already written a row for some of these same
        # `(api, method, path)` keys straight from `spec_content`. This
        # upserts the hand-authored text on top of that so it always wins,
        # instead of colliding with `ApiEndpoint`'s `(api, method, path)`
        # uniqueness constraint.
        endpoints = {}
        for spec in ENDPOINTS:
            endpoint, _created = ApiEndpoint.objects.update_or_create(
                api=apis[spec["api"]],
                method=spec["method"],
                path=spec["path"],
                defaults={
                    "operation_id": spec.get("operation_id", ""),
                    "summary": spec.get("summary", ""),
                    "description": spec.get("description", ""),
                    "deprecated": spec.get("deprecated", False),
                    "tags": spec.get("tags", []),
                    "request": spec.get("request", {}),
                    "responses": spec.get("responses", []),
                    "status": spec.get("status", ApiEndpoint.STATUS_ACTIVE),
                },
            )
            endpoints[(spec["api"], spec["method"], spec["path"])] = endpoint
        self.stdout.write(f"Created {len(endpoints)} endpoints")
        return endpoints

    def _create_endpoint_usages(
        self,
        endpoints: dict[tuple[str, str, str], ApiEndpoint],
        components: dict[str, CatalogEntity],
        apis: dict[str, CatalogEntity],
    ) -> None:
        # `add_consumed_api` is the same extension-point function a real Link
        # Service action calls — using it here, rather
        # than setting `consumes_apis` directly, keeps the seeded state
        # consistent with what the feature actually produces.
        admin_account = (
            get_user_model().objects.filter(username="admin").first()
        )
        for spec in ENDPOINT_USAGES:
            endpoint = endpoints[(spec["api"], spec["method"], spec["path"])]
            service = components[spec["service"]]
            ServiceEndpointUsage.objects.create(
                endpoint=endpoint, service=service, created_by=admin_account
            )
            add_consumed_api(service, apis[spec["api"]])
        self.stdout.write(
            f"Created {len(ENDPOINT_USAGES)} endpoint-service links"
        )

    def _lookup_operations(
        self, apis: dict[str, CatalogEntity]
    ) -> dict[tuple[str, str], ApiOperation]:
        # `_create_apis` already triggered `atlas_plugin_apis.asyncapi_import.
        # sync_operations_from_spec` (via `ApiDetails`'s `post_save` signal) for
        # every asyncapi-typed API above, writing `ApiOperation` rows straight
        # from `spec_content` — unlike `_create_endpoints`'s OpenAPI
        # counterpart, there's no hand-authored overlay to upsert on top
        # of it — this just reads
        # what the importer already produced.
        names_by_entity_id = {entity.id: name for name, entity in apis.items()}
        operations = {}
        for operation in ApiOperation.objects.filter(api__in=apis.values()):
            api_name = names_by_entity_id[operation.api_id]
            operations[(api_name, operation.operation_key)] = operation
        self.stdout.write(f"Found {len(operations)} operations")
        return operations

    def _create_operation_usages(
        self,
        operations: dict[tuple[str, str], ApiOperation],
        components: dict[str, CatalogEntity],
    ) -> None:
        # No `add_consumed_api`-style side effect here (unlike endpoint usages):
        # linking a Service to an Operation doesn't touch `ComponentDetails` at
        # all.
        admin_account = (
            get_user_model().objects.filter(username="admin").first()
        )
        for spec in OPERATION_USAGES:
            operation = operations[(spec["api"], spec["operation_key"])]
            service = components[spec["service"]]
            ServiceOperationUsage.objects.create(
                operation=operation,
                service=service,
                role=spec["role"],
                created_by=admin_account,
            )
        self.stdout.write(
            f"Created {len(OPERATION_USAGES)} operation-service links"
        )

    def _create_guest_actor(self) -> CatalogEntity:
        entity = CatalogEntity.objects.create(
            kind=KIND_ACTOR, name=GUEST_ACTOR["name"]
        )
        ActorDetails.objects.create(
            entity=entity,
            display_name=GUEST_ACTOR["display_name"],
            email=GUEST_ACTOR["email"],
        )
        self.stdout.write("Created 1 guest actor")
        return entity

    def _create_architecture_relationships(
        self,
        components: dict[str, CatalogEntity],
        apis: dict[str, CatalogEntity],
        resources: dict[str, CatalogEntity],
        guest: CatalogEntity,
    ) -> None:
        targets_by_kind: dict[str, dict[str, CatalogEntity]] = {
            "component": components,
            "api": apis,
            "resource": resources,
        }
        tags = {
            tag for spec in ARCHITECTURE_RELATIONSHIPS for tag in spec["tags"]
        }
        tags.update(
            tag
            for spec in ACTOR_ARCHITECTURE_RELATIONSHIPS
            for tag in spec["tags"]
        )
        ensure_tags_exist(list(tags))
        for spec in ARCHITECTURE_RELATIONSHIPS:
            source = components[spec["source"]]
            target = targets_by_kind[spec["target_kind"]][spec["target"]]
            ArchitectureRelationship.objects.create(
                source=source,
                target=target,
                label=spec["label"],
                technology=spec["technology"],
                interaction_kind=spec["interaction_kind"],
                tags=spec["tags"],
            )
        for spec in ACTOR_ARCHITECTURE_RELATIONSHIPS:
            target = targets_by_kind[spec["target_kind"]][spec["target"]]
            ArchitectureRelationship.objects.create(
                source=guest,
                target=target,
                label=spec["label"],
                technology=spec["technology"],
                interaction_kind=spec["interaction_kind"],
                tags=spec["tags"],
            )
        total = len(ARCHITECTURE_RELATIONSHIPS) + len(
            ACTOR_ARCHITECTURE_RELATIONSHIPS
        )
        self.stdout.write(f"Created {total} architecture relationships")

    def _create_flows(
        self,
        systems: dict[str, CatalogEntity],
        apis: dict[str, CatalogEntity],
        endpoints: dict[tuple[str, str, str], ApiEndpoint],
        operations: dict[tuple[str, str], ApiOperation],
    ) -> None:
        for spec in FLOWS:
            Flow.objects.create(
                system=systems[spec["system"]],
                name=spec["name"],
                description=spec["description"],
                documentation=documentation_for("flow", spec),
                steps=[
                    _resolve_flow_step(step, apis, endpoints, operations)
                    for step in spec["steps"]
                ],
            )
        self.stdout.write(f"Created {len(FLOWS)} flows")

    def _color_tags(self) -> None:
        """Assign every non-External demo tag a stable, visibly distinct
        palette color."""
        for tag in Tag.objects.exclude(name="External").order_by("name"):
            if not (color := TAG_COLOR_MAP.get(tag.name)):
                color = TAG_COLOR_CHOICES[
                    sum(tag.name.encode()) % len(TAG_COLOR_CHOICES)
                ]

            tag.color = color
            tag.save(update_fields=["color"])
