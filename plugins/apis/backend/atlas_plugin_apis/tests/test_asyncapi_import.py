"""Tests for the AsyncAPI (2.x/3.0) importer — parser unit tests, upsert/lifecycle tests, failure-path
tests, and a `post_save` signal re-entrancy regression test.

Integration tests for the two write paths that trigger a sync live alongside
their existing suites instead of here, per this codebase's convention of one
test module per write path (see `test_openapi_import.py`'s own docstring):
`server.apps.catalog.tests.test_api_spec` (create/patch via
`atlas_plugin_apis.api.views`) and
`atlas_plugin_ingestion.tests.test_spec_refresh` (the periodic
`due_for_spec_refresh` refresh). This module also exercises those
same write paths directly against `sync_operations_from_spec`/
`due_for_spec_refresh` for convenience, without needing to duplicate this
plugin's own HTTP-layer test setup.
"""

from unittest.mock import patch

import pytest
from atlas_plugin_api import SafeHttpResponse
from server.apps.catalog.tests.factories import (
    create_api,
    create_component,
    create_system,
)

from atlas_plugin_apis import asyncapi_import
from atlas_plugin_apis import signals as signals_module
from atlas_plugin_apis.asyncapi_import import (
    SpecParseError,
    detect_spec_version,
    parse_operations,
    sync_operations_from_spec,
)
from atlas_plugin_apis.extension_points import due_for_spec_refresh
from atlas_plugin_apis.models import (
    ApiDetails,
    ApiOperation,
    ServiceOperationUsage,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def system(group):
    return create_system(name="core", owner=group)


@pytest.fixture
def api(group, system):
    return create_api(
        name="notifications-api",
        owner=group,
        system=system,
        type=ApiDetails.TYPE_ASYNCAPI,
    )


ASYNCAPI_2X_SPEC = """
asyncapi: 2.6.0
info: {title: Notifications, version: "1.0"}
servers:
  production:
    url: broker.demo.atlas.local:9092
    protocol: kafka
channels:
  booking.confirmed:
    publish:
      operationId: onBookingConfirmed
      summary: Receive booking-confirmation events
      description: Consumed to notify the guest and host.
      tags:
        - name: bookings
      message:
        name: BookingConfirmed
        payload:
          type: object
          properties:
            booking_id: {type: string}
          required: [booking_id]
        examples:
          - payload: {booking_id: booking_123}
  notification.delivery-status:
    subscribe:
      operationId: publishDeliveryStatus
      summary: Publish a delivery-status update
      message:
        payload: {"$ref": "#/components/schemas/DeliveryStatus"}
  multi.shape:
    publish:
      operationId: onMultiShape
      message:
        oneOf:
          - name: ShapeA
            payload: {type: object, properties: {a: {type: string}}}
          - name: ShapeB
            payload: {type: object, properties: {b: {type: string}}}
  order.delivered:
    publish:
      operationId: onOrderDelivered
      message:
        $ref: '#/components/messages/OrderDelivered'
components:
  schemas:
    DeliveryStatus:
      type: object
      properties:
        status: {type: string}
  messages:
    OrderDelivered:
      name: OrderDelivered
      payload:
        type: object
        properties:
          order_id: {type: string}
"""

ASYNCAPI_2X_MULTIPLE_SERVERS = """
asyncapi: 2.6.0
info: {title: Notifications, version: "1.0"}
servers:
  primary: {url: broker-a.demo.atlas.local:9092, protocol: kafka}
  secondary: {url: broker-b.demo.atlas.local:9092, protocol: amqp}
channels:
  booking.confirmed:
    publish:
      summary: Receive booking-confirmation events
"""

ASYNCAPI_3X_SPEC = """
asyncapi: 3.0.0
info: {title: Notifications, version: "1.0"}
servers:
  production:
    host: broker.demo.atlas.local:9092
    protocol: kafka
channels:
  bookingConfirmed:
    address: booking.confirmed
    servers:
      - $ref: '#/servers/production'
    messages:
      BookingConfirmed:
        payload:
          type: object
          properties:
            booking_id: {type: string}
        examples:
          - payload: {booking_id: booking_123}
  orderCreated:
    address: order.created
    messages:
      OrderCreated:
        $ref: '#/components/messages/OrderCreated'
operations:
  onBookingConfirmed:
    action: receive
    channel: {$ref: '#/channels/bookingConfirmed'}
    title: onBookingConfirmed
    summary: Receive booking-confirmation events
    messages:
      - $ref: '#/channels/bookingConfirmed/messages/BookingConfirmed'
  onOrderCreated:
    action: receive
    channel: {$ref: '#/channels/orderCreated'}
    messages:
      - $ref: '#/channels/orderCreated/messages/OrderCreated'
  onUnresolvedMessage:
    action: send
    channel: {$ref: '#/channels/bookingConfirmed'}
    messages:
      - $ref: '#/components/messages/TrulyMissing'
components:
  messages:
    OrderCreated:
      name: OrderCreated
      payload:
        type: object
        properties:
          order_id: {type: string}
"""

SIMPLE_2X_SPEC = """
asyncapi: 2.6.0
info: {title: Notifications, version: "1.0"}
channels:
  booking.confirmed:
    publish:
      summary: Receive booking-confirmation events
"""

SIMPLE_2X_SPEC_CHANGED = """
asyncapi: 2.6.0
info: {title: Notifications, version: "1.0"}
channels:
  booking.confirmed:
    publish:
      summary: Receive booking-confirmation events (updated)
"""

SIMPLE_2X_SPEC_EMPTY_CHANNELS = """
asyncapi: 2.6.0
info: {title: Notifications, version: "1.0"}
channels: {}
"""


# --- Version detection (8.1) -------------------------------------------------


def test_detect_spec_version_recognizes_2x():
    assert detect_spec_version(ASYNCAPI_2X_SPEC) == asyncapi_import.VERSION_2X


def test_detect_spec_version_recognizes_3x():
    assert detect_spec_version(ASYNCAPI_3X_SPEC) == asyncapi_import.VERSION_3X


def test_detect_spec_version_returns_none_for_unrecognized_document():
    assert detect_spec_version("foo: bar") is None


# --- 2.x parsing / direction mapping (8.1) -----------------------------------


def test_2x_publish_is_imported_as_receive():
    operations = parse_operations(ASYNCAPI_2X_SPEC)
    op = next(o for o in operations if o.channel_address == "booking.confirmed")
    assert op.direction == ApiOperation.DIRECTION_RECEIVE


def test_2x_subscribe_is_imported_as_send():
    operations = parse_operations(ASYNCAPI_2X_SPEC)
    op = next(
        o for o in operations if o.channel_address == "notification.delivery-status"
    )
    assert op.direction == ApiOperation.DIRECTION_SEND


def test_2x_operation_key_is_channel_plus_direction():
    operations = parse_operations(ASYNCAPI_2X_SPEC)
    op = next(o for o in operations if o.channel_address == "booking.confirmed")
    assert op.operation_key == "booking.confirmed-receive"


def test_2x_documentation_fields_are_mapped():
    operations = parse_operations(ASYNCAPI_2X_SPEC)
    op = next(o for o in operations if o.channel_address == "booking.confirmed")
    assert op.operation_id == "onBookingConfirmed"
    assert op.summary == "Receive booking-confirmation events"
    assert op.description == "Consumed to notify the guest and host."
    assert op.tags == ["bookings"]


# --- 3.0 parsing / direction passthrough (8.1) -------------------------------


def test_3x_action_passes_through_unchanged():
    operations = parse_operations(ASYNCAPI_3X_SPEC)
    op = next(o for o in operations if o.operation_key == "onBookingConfirmed")
    assert op.direction == ApiOperation.DIRECTION_RECEIVE


def test_3x_operation_key_uses_operations_map_key():
    operations = parse_operations(ASYNCAPI_3X_SPEC)
    keys = {o.operation_key for o in operations}
    assert "onBookingConfirmed" in keys


def test_3x_resolves_channel_address_from_referenced_channel():
    operations = parse_operations(ASYNCAPI_3X_SPEC)
    op = next(o for o in operations if o.operation_key == "onBookingConfirmed")
    assert op.channel_address == "booking.confirmed"


# --- channel_protocol resolution (8.1) ---------------------------------------


def test_2x_single_server_resolves_protocol():
    operations = parse_operations(ASYNCAPI_2X_SPEC)
    op = next(o for o in operations if o.channel_address == "booking.confirmed")
    assert op.channel_protocol == "kafka"


def test_2x_multiple_servers_leave_protocol_unresolved():
    operations = parse_operations(ASYNCAPI_2X_MULTIPLE_SERVERS)
    [op] = operations
    assert op.channel_protocol == ""


def test_3x_channel_referencing_one_server_resolves_protocol():
    operations = parse_operations(ASYNCAPI_3X_SPEC)
    op = next(o for o in operations if o.operation_key == "onBookingConfirmed")
    assert op.channel_protocol == "kafka"


# --- Message mapping (8.1) ---------------------------------------------------


def test_payload_and_first_example_are_mapped_to_schema_and_example():
    operations = parse_operations(ASYNCAPI_2X_SPEC)
    op = next(o for o in operations if o.channel_address == "booking.confirmed")
    [message] = op.message
    assert message["name"] == "BookingConfirmed"
    assert message["schema"] == {
        "type": "object",
        "properties": {"booking_id": {"type": "string"}},
        "required": ["booking_id"],
    }
    assert message["example"] == {"booking_id": "booking_123"}


def test_ref_payload_resolves_to_expanded_schema():
    operations = parse_operations(ASYNCAPI_2X_SPEC)
    op = next(
        o for o in operations if o.channel_address == "notification.delivery-status"
    )
    [message] = op.message
    assert message["schema"] == {
        "type": "object",
        "properties": {"status": {"type": "string"}},
    }


def test_2x_bare_ref_message_field_resolves():
    """The 2.x analogue of the 3.0 channel-map-entry indirection — no prior
    test covered a bare `{"$ref": ...}` `publish`/`subscribe` message field
    """
    operations = parse_operations(ASYNCAPI_2X_SPEC)
    op = next(o for o in operations if o.channel_address == "order.delivered")
    [message] = op.message
    assert message["name"] == "OrderDelivered"
    assert message["schema"] == {
        "type": "object",
        "properties": {"order_id": {"type": "string"}},
    }


def test_oneof_message_produces_multiple_entries():
    operations = parse_operations(ASYNCAPI_2X_SPEC)
    op = next(o for o in operations if o.channel_address == "multi.shape")
    assert {m["name"] for m in op.message} == {"ShapeA", "ShapeB"}


def test_3x_dangling_message_reference_yields_name_only_entry():
    operations = parse_operations(ASYNCAPI_3X_SPEC)
    op = next(o for o in operations if o.operation_key == "onUnresolvedMessage")
    [message] = op.message
    assert message["name"] == "TrulyMissing"
    assert message["schema"] is None
    assert message["example"] is None


def test_3x_channel_map_entry_that_is_itself_a_ref_is_dereferenced_into_components():
    """The motivating "Orders Events API" shape: an operation's `messages[]`
    entry `$ref`s into a channel's own `messages` map, whose entry is itself
    only a `$ref` into `components.messages` (previously this fixture
    shape fell back to a name-only stub)."""
    operations = parse_operations(ASYNCAPI_3X_SPEC)
    op = next(o for o in operations if o.operation_key == "onOrderCreated")
    [message] = op.message
    assert message["name"] == "OrderCreated"
    assert message["schema"] == {
        "type": "object",
        "properties": {"order_id": {"type": "string"}},
    }


# --- $ref resolution: multi-hop chains, cycles, siblings --

ASYNCAPI_SELF_REFERENTIAL_SPEC = """
asyncapi: 2.6.0
info: {title: Notifications, version: "1.0"}
channels:
  category.updated:
    publish:
      operationId: onCategoryUpdated
      message:
        name: CategoryUpdated
        payload:
          $ref: '#/components/schemas/Category'
components:
  schemas:
    Category:
      type: object
      properties:
        name: {type: string}
        children:
          type: array
          items: {"$ref": "#/components/schemas/Category"}
"""


def test_self_referential_payload_schema_syncs_successfully_without_looping(api):
    details = api.api_details
    details.spec_content = ASYNCAPI_SELF_REFERENTIAL_SPEC

    sync_operations_from_spec(details)

    details.refresh_from_db()
    assert details.operations_sync_failed is False
    operation = ApiOperation.objects.get(api=api, channel_address="category.updated")
    [message] = operation.message
    assert message["schema"]["properties"]["children"]["items"] == {
        "$ref": "#/components/schemas/Category"
    }


ASYNCAPI_3X_MULTI_HOP_SPEC = """
asyncapi: 3.0.0
info: {title: Notifications, version: "1.0"}
channels:
  orderShipped:
    address: order.shipped
    messages:
      OrderShipped:
        $ref: '#/components/messages/Alias1'
operations:
  onOrderShipped:
    action: receive
    channel: {$ref: '#/channels/orderShipped'}
    messages:
      - $ref: '#/channels/orderShipped/messages/OrderShipped'
components:
  messages:
    Alias1:
      $ref: '#/components/messages/Alias2'
    Alias2:
      name: OrderShippedReal
      payload:
        type: object
        properties:
          tracking_id: {type: string}
"""


def test_3x_multi_hop_message_reference_chain_resolves_fully():
    """More than the one extra hop the motivating "Orders Events API" spec
    needed: channel-map entry -> $ref -> another $ref -> the real inline
    message."""
    [op] = parse_operations(ASYNCAPI_3X_MULTI_HOP_SPEC)
    [message] = op.message
    assert message["name"] == "OrderShippedReal"
    assert message["schema"] == {
        "type": "object",
        "properties": {"tracking_id": {"type": "string"}},
    }


ASYNCAPI_3X_CYCLIC_CHAIN_SPEC = """
asyncapi: 3.0.0
info: {title: Notifications, version: "1.0"}
channels:
  loopy:
    address: loopy
    messages:
      Loopy:
        $ref: '#/components/messages/AliasA'
operations:
  onLoopy:
    action: receive
    channel: {$ref: '#/channels/loopy'}
    messages:
      - $ref: '#/channels/loopy/messages/Loopy'
components:
  messages:
    AliasA:
      $ref: '#/components/messages/AliasB'
    AliasB:
      $ref: '#/components/messages/AliasA'
"""


def test_3x_cyclic_message_reference_chain_falls_back_to_a_stub_without_looping():
    [op] = parse_operations(ASYNCAPI_3X_CYCLIC_CHAIN_SPEC)
    [message] = op.message
    assert message["name"] == "Loopy"
    assert message["schema"] is None
    assert message["example"] is None


ASYNCAPI_3X_IMPLICIT_MESSAGES_SPEC = """
asyncapi: 3.0.0
info: {title: Notifications, version: "1.0"}
channels:
  inventory:
    address: inventory.updated
    messages:
      StockChanged:
        $ref: '#/components/messages/StockChanged'
operations:
  onInventoryUpdated:
    action: receive
    channel: {$ref: '#/channels/inventory'}
components:
  messages:
    StockChanged:
      name: StockChanged
      payload:
        type: object
        properties:
          sku: {type: string}
"""


def test_3x_implicit_message_set_dereferences_ref_entries_too():
    """No `messages[]` narrowing on the operation — every channel-map entry
    is in scope, including one that's itself still a `$ref`."""
    [op] = parse_operations(ASYNCAPI_3X_IMPLICIT_MESSAGES_SPEC)
    [message] = op.message
    assert message["name"] == "StockChanged"
    assert message["schema"] == {
        "type": "object",
        "properties": {"sku": {"type": "string"}},
    }


ASYNCAPI_SIBLING_NOT_PRESERVED_SPEC = """
asyncapi: 2.6.0
info: {title: Notifications, version: "1.0"}
channels:
  booking.confirmed:
    publish:
      operationId: onBookingConfirmed
      message:
        name: BookingConfirmed
        payload:
          $ref: '#/components/schemas/BookingSchema'
          description: override
components:
  schemas:
    BookingSchema:
      type: object
      properties:
        id: {type: string}
"""


def test_sibling_key_next_to_a_payload_ref_is_not_preserved():
    """Contrast with the OpenAPI-side sibling-merge behavior
    (`test_openapi_import.py::test_sibling_key_next_to_a_ref_is_merged_onto_the_resolved_schema`)
    — AsyncAPI's Reference Object semantics discard siblings."""
    [op] = parse_operations(ASYNCAPI_SIBLING_NOT_PRESERVED_SPEC)
    [message] = op.message
    assert message["schema"] == {
        "type": "object",
        "properties": {"id": {"type": "string"}},
    }


ASYNCAPI_3X_PAYLOAD_LESS_SPEC = """
asyncapi: 3.0.0
info: {title: Notifications, version: "1.0"}
channels:
  heartbeat:
    address: heartbeat
    messages:
      Heartbeat:
        name: Heartbeat
        title: Heartbeat Signal
operations:
  onHeartbeatExplicit:
    action: receive
    channel: {$ref: '#/channels/heartbeat'}
    messages:
      - $ref: '#/channels/heartbeat/messages/Heartbeat'
  onHeartbeatImplicit:
    action: receive
    channel: {$ref: '#/channels/heartbeat'}
"""


def test_3x_payload_less_message_is_mapped_not_stubbed_explicit_narrowing():
    operations = parse_operations(ASYNCAPI_3X_PAYLOAD_LESS_SPEC)
    op = next(o for o in operations if o.operation_key == "onHeartbeatExplicit")
    [message] = op.message
    assert message["name"] == "Heartbeat"
    assert message["title"] == "Heartbeat Signal"
    assert message["schema"] is None


def test_3x_payload_less_message_is_mapped_not_stubbed_implicit_narrowing():
    operations = parse_operations(ASYNCAPI_3X_PAYLOAD_LESS_SPEC)
    op = next(o for o in operations if o.operation_key == "onHeartbeatImplicit")
    [message] = op.message
    assert message["name"] == "Heartbeat"
    assert message["title"] == "Heartbeat Signal"
    assert message["schema"] is None


# --- message headers / operation externalDocs --

ASYNCAPI_2X_HEADERS_AND_EXTERNAL_DOCS_SPEC = """
asyncapi: 2.6.0
info: {title: Notifications, version: "1.0"}
channels:
  booking.confirmed:
    publish:
      operationId: onBookingConfirmed
      externalDocs:
        description: Booking confirmation docs
        url: https://docs.example.com/booking-confirmed
      message:
        name: BookingConfirmed
        payload:
          type: object
          properties:
            booking_id: {type: string}
        headers:
          $ref: '#/components/schemas/Envelope'
  no.headers:
    publish:
      summary: No headers here
      message:
        name: Plain
        payload: {type: object}
  no.external.docs.url:
    publish:
      summary: externalDocs with no url
      externalDocs:
        description: Missing URL
components:
  schemas:
    Envelope:
      type: object
      properties:
        correlationId: {type: string}
      required: [correlationId]
"""

ASYNCAPI_3X_HEADERS_AND_EXTERNAL_DOCS_SPEC = """
asyncapi: 3.0.0
info: {title: Notifications, version: "1.0"}
channels:
  bookingConfirmed:
    address: booking.confirmed
    messages:
      BookingConfirmed:
        payload:
          type: object
          properties:
            booking_id: {type: string}
        headers:
          $ref: '#/components/schemas/Envelope'
operations:
  onBookingConfirmed:
    action: receive
    channel: {$ref: '#/channels/bookingConfirmed'}
    externalDocs:
      description: Booking confirmation docs
      url: https://docs.example.com/booking-confirmed
    messages:
      - $ref: '#/channels/bookingConfirmed/messages/BookingConfirmed'
components:
  schemas:
    Envelope:
      type: object
      properties:
        correlationId: {type: string}
      required: [correlationId]
"""

ASYNCAPI_HEADERS_SELF_REFERENTIAL_SPEC = """
asyncapi: 2.6.0
info: {title: Notifications, version: "1.0"}
channels:
  category.updated:
    publish:
      operationId: onCategoryUpdated
      message:
        name: CategoryUpdated
        headers:
          $ref: '#/components/schemas/Category'
components:
  schemas:
    Category:
      type: object
      properties:
        name: {type: string}
        children:
          type: array
          items: {"$ref": "#/components/schemas/Category"}
"""


def test_2x_message_headers_ref_resolves_to_expanded_schema():
    operations = parse_operations(ASYNCAPI_2X_HEADERS_AND_EXTERNAL_DOCS_SPEC)
    op = next(o for o in operations if o.channel_address == "booking.confirmed")
    [message] = op.message
    assert message["headers"] == {
        "type": "object",
        "properties": {"correlationId": {"type": "string"}},
        "required": ["correlationId"],
    }


def test_3x_message_headers_ref_resolves_to_expanded_schema():
    operations = parse_operations(ASYNCAPI_3X_HEADERS_AND_EXTERNAL_DOCS_SPEC)
    [op] = operations
    [message] = op.message
    assert message["headers"] == {
        "type": "object",
        "properties": {"correlationId": {"type": "string"}},
        "required": ["correlationId"],
    }


def test_message_with_no_headers_yields_no_headers_key():
    operations = parse_operations(ASYNCAPI_2X_HEADERS_AND_EXTERNAL_DOCS_SPEC)
    op = next(o for o in operations if o.channel_address == "no.headers")
    [message] = op.message
    assert "headers" not in message


def test_self_referential_headers_schema_stops_at_the_cycle_without_looping():
    [op] = parse_operations(ASYNCAPI_HEADERS_SELF_REFERENTIAL_SPEC)
    [message] = op.message
    assert message["headers"]["properties"]["children"]["items"] == {
        "$ref": "#/components/schemas/Category"
    }


def test_2x_operation_external_docs_with_url_is_imported():
    operations = parse_operations(ASYNCAPI_2X_HEADERS_AND_EXTERNAL_DOCS_SPEC)
    op = next(o for o in operations if o.channel_address == "booking.confirmed")
    assert op.external_docs == {
        "description": "Booking confirmation docs",
        "url": "https://docs.example.com/booking-confirmed",
    }


def test_3x_operation_external_docs_with_url_is_imported():
    operations = parse_operations(ASYNCAPI_3X_HEADERS_AND_EXTERNAL_DOCS_SPEC)
    [op] = operations
    assert op.external_docs == {
        "description": "Booking confirmation docs",
        "url": "https://docs.example.com/booking-confirmed",
    }


def test_operation_external_docs_missing_url_yields_empty_external_docs():
    operations = parse_operations(ASYNCAPI_2X_HEADERS_AND_EXTERNAL_DOCS_SPEC)
    op = next(o for o in operations if o.channel_address == "no.external.docs.url")
    assert op.external_docs == {}
    assert op.summary == "externalDocs with no url"


def test_operation_with_no_external_docs_yields_empty_external_docs():
    operations = parse_operations(ASYNCAPI_2X_HEADERS_AND_EXTERNAL_DOCS_SPEC)
    op = next(o for o in operations if o.channel_address == "no.headers")
    assert op.external_docs == {}


def test_malformed_headers_block_is_skipped_and_logged_without_aborting_the_parse(
    caplog,
):
    """Exercises the same per-operation `try`/`except` in `_parse_channels_2x`
    that a malformed `externalDocs` block would also fall through to
    no dedicated error handling exists for either
    field, so triggering a raise from the shared `spec_refs.resolve_schema`
    call site (used for both `payload` and `headers`) is sufficient to cover
    both."""
    spec = """
asyncapi: 2.6.0
info: {title: Notifications, version: "1.0"}
channels:
  booking.confirmed:
    publish:
      summary: Good
  bad.headers:
    publish:
      summary: Bad headers
      message:
        name: BadHeaders
        headers: {type: object}
"""
    with patch(
        "atlas_plugin_apis.asyncapi_import.spec_refs.resolve_schema",
        side_effect=ValueError("boom"),
    ):
        operations = parse_operations(spec, api_label="notifications-api")
    assert [op.channel_address for op in operations] == ["booking.confirmed"]


# --- Malformed-entry skip / spec-level failures (8.1) ------------------------


def test_one_malformed_operation_is_skipped_and_logged_without_aborting_the_parse(
    caplog,
):
    spec = """
asyncapi: 2.6.0
info: {title: Notifications, version: "1.0"}
channels:
  booking.confirmed:
    publish:
      summary: Good
  bad.channel:
    publish: 5
"""
    operations = parse_operations(spec, api_label="notifications-api")
    assert [op.channel_address for op in operations] == ["booking.confirmed"]


def test_parse_operations_raises_for_unrecognized_version():
    with pytest.raises(SpecParseError):
        parse_operations("foo: bar")


def test_parse_operations_raises_for_missing_channels():
    with pytest.raises(SpecParseError):
        parse_operations("asyncapi: 2.6.0\ninfo: {}\n")


def test_parse_operations_raises_for_invalid_yaml():
    with pytest.raises(SpecParseError):
        parse_operations("not: yaml: [unterminated")


# --- Upsert / lifecycle (8.2) ------------------------------------------------


def test_new_operation_creates_an_apioperation(api):
    details = api.api_details
    details.spec_content = SIMPLE_2X_SPEC

    sync_operations_from_spec(details)

    operation = ApiOperation.objects.get(
        api=api, operation_key="booking.confirmed-receive"
    )
    assert operation.status == ApiOperation.STATUS_ACTIVE
    assert operation.summary == "Receive booking-confirmation events"


def test_changed_operation_updates_fields_and_preserves_id(api):
    details = api.api_details
    details.spec_content = SIMPLE_2X_SPEC
    sync_operations_from_spec(details)
    operation = ApiOperation.objects.get(
        api=api, operation_key="booking.confirmed-receive"
    )
    original_id = operation.id

    details.spec_content = SIMPLE_2X_SPEC_CHANGED
    sync_operations_from_spec(details)

    operation.refresh_from_db()
    assert operation.id == original_id
    assert operation.summary == "Receive booking-confirmation events (updated)"


def test_manual_deprecated_override_is_not_reset_by_reimport(api):
    """A manual deprecated override is independent of the source AsyncAPI
    document — re-syncing an
    unchanged channel must never clear a manually-set `deprecated` flag."""
    details = api.api_details
    details.spec_content = SIMPLE_2X_SPEC
    sync_operations_from_spec(details)
    operation = ApiOperation.objects.get(
        api=api, operation_key="booking.confirmed-receive"
    )
    operation.deprecated = True
    operation.save(update_fields=["deprecated"])

    # `SIMPLE_2X_SPEC_CHANGED` differs (a doc field changes), forcing
    # `_upsert_operation` down its `existing.save()` path — the strictest
    # check that `deprecated` isn't clobbered by a real re-import write.
    details.spec_content = SIMPLE_2X_SPEC_CHANGED
    sync_operations_from_spec(details)

    operation.refresh_from_db()
    assert operation.deprecated is True
    assert operation.summary == "Receive booking-confirmation events (updated)"


def test_operation_missing_from_reparse_soft_removes_and_preserves_service_links(
    api, group, system
):
    details = api.api_details
    details.spec_content = SIMPLE_2X_SPEC
    sync_operations_from_spec(details)
    operation = ApiOperation.objects.get(
        api=api, operation_key="booking.confirmed-receive"
    )
    service = create_component(name="notification-service", owner=group, system=system)
    usage = ServiceOperationUsage.objects.create(operation=operation, service=service)

    details.spec_content = SIMPLE_2X_SPEC_EMPTY_CHANNELS
    sync_operations_from_spec(details)

    operation.refresh_from_db()
    assert operation.status == ApiOperation.STATUS_REMOVED
    assert ApiOperation.objects.filter(pk=operation.pk).exists()
    assert ServiceOperationUsage.objects.filter(pk=usage.pk).exists()


def test_removed_operation_reappearing_revives_with_updated_fields_and_preserved_links(
    api, group, system
):
    details = api.api_details
    details.spec_content = SIMPLE_2X_SPEC
    sync_operations_from_spec(details)
    operation = ApiOperation.objects.get(
        api=api, operation_key="booking.confirmed-receive"
    )
    original_id = operation.id
    service = create_component(name="notification-service", owner=group, system=system)
    usage = ServiceOperationUsage.objects.create(operation=operation, service=service)

    details.spec_content = SIMPLE_2X_SPEC_EMPTY_CHANNELS
    sync_operations_from_spec(details)
    operation.refresh_from_db()
    assert operation.status == ApiOperation.STATUS_REMOVED

    details.spec_content = SIMPLE_2X_SPEC_CHANGED
    sync_operations_from_spec(details)

    operation.refresh_from_db()
    assert operation.status == ApiOperation.STATUS_ACTIVE
    assert operation.id == original_id
    assert operation.summary == "Receive booking-confirmation events (updated)"
    assert ServiceOperationUsage.objects.filter(pk=usage.pk).exists()


# --- Failure paths (8.3) ------------------------------------------------------


def test_unparseable_spec_sets_failure_flag_and_leaves_existing_operations_untouched(
    api,
):
    details = api.api_details
    details.spec_content = SIMPLE_2X_SPEC
    sync_operations_from_spec(details)
    operation = ApiOperation.objects.get(
        api=api, operation_key="booking.confirmed-receive"
    )

    details.spec_content = "not: yaml: [unterminated"
    sync_operations_from_spec(details)

    details.refresh_from_db()
    assert details.operations_sync_failed is True
    operation.refresh_from_db()
    assert operation.status == ApiOperation.STATUS_ACTIVE
    assert operation.summary == "Receive booking-confirmation events"


def test_one_malformed_channel_among_valid_ones_imports_the_rest_without_flagging_failure(
    api,
):
    spec = """
asyncapi: 2.6.0
info: {title: Notifications, version: "1.0"}
channels:
  booking.confirmed:
    publish:
      summary: Good
  bad.channel:
    publish: 5
"""
    details = api.api_details
    details.spec_content = spec

    sync_operations_from_spec(details)

    details.refresh_from_db()
    assert details.operations_sync_failed is False
    assert ApiOperation.objects.filter(
        api=api, channel_address="booking.confirmed"
    ).exists()
    assert not ApiOperation.objects.filter(
        api=api, channel_address="bad.channel"
    ).exists()


def test_successful_sync_clears_a_prior_failure_and_updates_timestamp(api):
    details = api.api_details
    details.spec_content = "not: yaml: [unterminated"
    sync_operations_from_spec(details)
    details.refresh_from_db()
    assert details.operations_sync_failed is True
    assert details.operations_synced_at is None

    details.spec_content = SIMPLE_2X_SPEC
    sync_operations_from_spec(details)

    details.refresh_from_db()
    assert details.operations_sync_failed is False
    assert details.operations_synced_at is not None


def test_non_asyncapi_typed_api_is_never_synced(group, system):
    entity = create_api(
        name="billing-api", owner=group, system=system, type=ApiDetails.TYPE_OPENAPI
    )
    details = entity.api_details
    details.spec_content = SIMPLE_2X_SPEC

    sync_operations_from_spec(details)

    assert not ApiOperation.objects.filter(api=entity).exists()
    details.refresh_from_db()
    assert details.operations_synced_at is None


def test_empty_spec_content_is_never_synced(api):
    details = api.api_details
    details.spec_content = ""

    sync_operations_from_spec(details)

    assert not ApiOperation.objects.filter(api=api).exists()
    details.refresh_from_db()
    assert details.operations_synced_at is None


# --- Periodic refresh write path (4.4/8.4) -----------------------------------
#
# `atlas_plugin_ingestion.pipeline.refresh_spec_urls` is a thin wrapper around
# `due_for_spec_refresh` (extension_points.py docstring), so exercising the
# latter directly here covers that write path without this plugin's tests
# needing to import `atlas_plugin_ingestion` (no such dependency exists today).

SPEC_FETCH_PATCH_TARGET = "atlas_plugin_apis.spec_fetch.safe_request"


def test_due_for_spec_refresh_syncs_operations_from_the_newly_fetched_spec(api):
    details = api.api_details
    details.spec_source = ApiDetails.SPEC_SOURCE_URL
    details.spec_url = "https://example.com/asyncapi.yaml"
    details.save()

    with patch(SPEC_FETCH_PATCH_TARGET) as mock_get:
        mock_get.return_value = SafeHttpResponse(
            status_code=200,
            headers={},
            url="https://example.com/asyncapi.yaml",
            resolved_address="203.0.113.1",
            content=SIMPLE_2X_SPEC.encode(),
        )
        due_for_spec_refresh()

    operation = ApiOperation.objects.get(
        api=api, operation_key="booking.confirmed-receive"
    )
    assert operation.summary == "Receive booking-confirmation events"
    details.refresh_from_db()
    assert details.operations_sync_failed is False
    assert details.operations_synced_at is not None


# --- Signal wiring / re-entrancy regression (4.2/8.5) ------------------------


def test_post_save_receiver_skips_sync_for_saves_scoped_to_sync_status_fields(api):
    details = api.api_details

    with patch(
        "atlas_plugin_apis.asyncapi_import.sync_operations_from_spec"
    ) as mock_sync:
        signals_module._sync_operations_on_save(
            ApiDetails,
            details,
            update_fields=frozenset({"operations_synced_at", "operations_sync_failed"}),
        )
        mock_sync.assert_not_called()

        signals_module._sync_operations_on_save(
            ApiDetails, details, update_fields=frozenset({"spec_content"})
        )
        mock_sync.assert_called_once_with(details)

        signals_module._sync_operations_on_save(ApiDetails, details, update_fields=None)
        assert mock_sync.call_count == 2


def test_self_save_after_a_sync_does_not_retrigger_a_second_sync_pass(api):
    details = api.api_details
    details.spec_content = SIMPLE_2X_SPEC

    with patch(
        "atlas_plugin_apis.asyncapi_import.parse_operations",
        wraps=asyncapi_import.parse_operations,
    ) as parse_spy:
        details.save(update_fields=["spec_content"])

    assert parse_spy.call_count == 1
    details.refresh_from_db()
    assert details.operations_sync_failed is False
    assert details.operations_synced_at is not None
    assert ApiOperation.objects.filter(
        api=api, channel_address="booking.confirmed"
    ).exists()


def test_endpoints_status_self_save_does_not_retrigger_an_operations_sync_pass(api):
    """The two receivers share `_SYNC_STATUS_FIELDS` —
    an OpenAPI-sync self-save must not cause the AsyncAPI receiver to re-run
    either, and vice versa (covered by `test_openapi_import.py`'s own
    analogous test)."""
    details = api.api_details

    with patch(
        "atlas_plugin_apis.asyncapi_import.sync_operations_from_spec"
    ) as mock_sync:
        details.save(update_fields=["endpoints_synced_at", "endpoints_sync_failed"])
        mock_sync.assert_not_called()


# --- AMQP event key and delivery ---------------------------------------------

AMQP_3X_SPEC = """
asyncapi: 3.0.0
info: {title: Orders, version: "1.0"}
servers:
  broker: {host: rabbit.local, protocol: amqp}
channels:
  exchange-1:
    address: exchange-1
    servers: [{$ref: '#/servers/broker'}]
    bindings:
      amqp:
        exchange: {name: exchange-1, vhost: vhost-1}
  queue-1:
    address: queue-1
    servers: [{$ref: '#/servers/broker'}]
    bindings:
      amqp:
        queue: {name: queue-1, vhost: vhost-1}
operations:
  exchange-1:
    action: send
    channel: {$ref: '#/channels/exchange-1'}
    bindings:
      amqp:
        cc: ["  rk-a  "]
  queue-1:
    action: receive
    channel: {$ref: '#/channels/queue-1'}
    bindings:
      amqp:
        cc: [rk-a]
  empty-cc:
    action: receive
    channel: {$ref: '#/channels/queue-1'}
    bindings:
      amqp:
        cc: ["  "]
  no-cc:
    action: receive
    channel: {$ref: '#/channels/queue-1'}
  wildcard:
    action: receive
    channel: {$ref: '#/channels/queue-1'}
    bindings:
      amqp:
        cc: ["orders.event.#"]
"""

AMQP_2X_SPEC = """
asyncapi: 2.6.0
info: {title: Orders, version: "1.0"}
servers:
  broker: {url: rabbit.local, protocol: amqp}
channels:
  "rk-a:exchange-1:Publisher":
    bindings:
      amqp:
        exchange: {name: exchange-1, vhost: vhost-1}
    subscribe:
      bindings:
        amqp:
          cc: rk-a
  "rk-a:exchange-1:HandleEvent":
    bindings:
      amqp:
        queue: {name: queue-1}
    publish:
      bindings:
        amqp:
          cc: rk-a
  "plain:exchange-1:Publisher":
    subscribe:
      bindings:
        amqp:
          cc: ""
"""

AMQP_BINDINGS_NO_SERVERS_2X = """
asyncapi: 2.6.0
info: {title: Orders, version: "1.0"}
channels:
  "rk-a:exchange-1:Publisher":
    subscribe:
      bindings: {amqp: {cc: rk-a}}
  other-channel:
    subscribe:
      bindings: {kafka: {key: ignored}}
"""

KAFKA_WITH_CC_SPEC = """
asyncapi: 2.6.0
info: {title: Orders, version: "1.0"}
servers:
  broker: {url: kafka.local, protocol: kafka}
channels:
  orders.created:
    subscribe:
      bindings: {amqp: {cc: should-be-ignored}}
"""


def _by_key(spec):
    return {op.operation_key: op for op in parse_operations(spec)}


def test_3x_publisher_and_subscriber_share_the_trimmed_cc_as_event_key():
    operations = _by_key(AMQP_3X_SPEC)

    assert operations["exchange-1"].channel_address == "rk-a"
    assert operations["queue-1"].channel_address == "rk-a"


def test_3x_delivery_comes_from_the_channel_bindings():
    operations = _by_key(AMQP_3X_SPEC)

    assert operations["exchange-1"].delivery == {
        "exchange": "exchange-1",
        "vhost": "vhost-1",
    }
    assert operations["queue-1"].delivery == {"queue": "queue-1", "vhost": "vhost-1"}


def test_3x_missing_or_empty_cc_falls_back_to_the_channel_address():
    operations = _by_key(AMQP_3X_SPEC)

    assert operations["empty-cc"].channel_address == "queue-1"
    assert operations["no-cc"].channel_address == "queue-1"


def test_wildcard_cc_is_kept_literal():
    assert _by_key(AMQP_3X_SPEC)["wildcard"].channel_address == "orders.event.#"


def test_3x_operation_key_is_unchanged_by_the_event_key():
    assert _by_key(AMQP_3X_SPEC)["exchange-1"].operation_key == "exchange-1"


def test_2x_string_cc_replaces_the_composite_channel_key():
    operations = _by_key(AMQP_2X_SPEC)

    assert operations["rk-a:exchange-1:Publisher-send"].channel_address == "rk-a"
    assert operations["rk-a:exchange-1:Publisher-send"].delivery == {
        "exchange": "exchange-1",
        "vhost": "vhost-1",
    }
    assert operations["rk-a:exchange-1:HandleEvent-receive"].delivery == {
        "queue": "queue-1"
    }


def test_2x_publisher_and_listener_of_one_key_keep_distinct_operation_keys():
    operations = parse_operations(AMQP_2X_SPEC)
    keyed = [op for op in operations if op.channel_address == "rk-a"]

    assert len(keyed) == 2
    assert len({op.operation_key for op in keyed}) == 2


def test_2x_empty_cc_falls_back_to_the_channel_key():
    assert (
        _by_key(AMQP_2X_SPEC)["plain:exchange-1:Publisher-send"].channel_address
        == "plain:exchange-1:Publisher"
    )


def test_unresolved_protocol_applies_adapter_only_with_amqp_bindings():
    operations = _by_key(AMQP_BINDINGS_NO_SERVERS_2X)

    assert operations["rk-a:exchange-1:Publisher-send"].channel_address == "rk-a"
    assert operations["other-channel-send"].channel_address == "other-channel"
    assert operations["other-channel-send"].delivery == {}


def test_non_amqp_document_keeps_channel_address_and_has_no_delivery():
    (operation,) = parse_operations(KAFKA_WITH_CC_SPEC)

    assert operation.channel_address == "orders.created"
    assert operation.delivery == {}


def test_exchange_is_not_part_of_the_event_key():
    other_exchange = AMQP_3X_SPEC.replace("name: exchange-1", "name: exchange-2")

    assert (
        _by_key(other_exchange)["exchange-1"].channel_address
        == _by_key(AMQP_3X_SPEC)["exchange-1"].channel_address
    )


def test_reimport_updates_event_key_in_place_keeping_id_and_links(api, group, system):
    details = api.api_details
    details.spec_content = AMQP_3X_SPEC.replace('cc: ["  rk-a  "]', "cc: [old-key]")
    sync_operations_from_spec(details)
    operation = ApiOperation.objects.get(api=api, operation_key="exchange-1")
    assert operation.channel_address == "old-key"
    service = create_component(name="svc", owner=group, system=system)
    ServiceOperationUsage.objects.create(
        operation=operation, service=service, role="subscriber"
    )

    details.spec_content = AMQP_3X_SPEC
    sync_operations_from_spec(details)

    refreshed = ApiOperation.objects.get(api=api, operation_key="exchange-1")
    assert refreshed.id == operation.id
    assert refreshed.channel_address == "rk-a"
    assert refreshed.delivery == {"exchange": "exchange-1", "vhost": "vhost-1"}
    assert refreshed.service_usages.count() == 1
