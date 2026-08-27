"""Tests for the OpenAPI/Swagger importer — parser unit tests, upsert/lifecycle tests, failure-path
tests, and a `post_save` signal re-entrancy regression test.

Integration tests for the three write paths that trigger a sync live
alongside their existing suites instead of here, per this codebase's
convention of one test module per write path: `server.apps.catalog.tests.
test_api_spec` (create/patch via `atlas_plugin_apis.api.views`) and
`atlas_plugin_ingestion.tests.test_spec_refresh` (the periodic `due_for_
spec_refresh` refresh).
"""

from unittest.mock import patch

import pytest
import yaml
from atlas_plugin_api import SafeHttpResponse
from server.apps.catalog.tests.factories import (
    create_api,
    create_component,
    create_system,
)

from atlas_plugin_apis import openapi_import
from atlas_plugin_apis import signals as signals_module
from atlas_plugin_apis.extension_points import due_for_spec_refresh
from atlas_plugin_apis.models import ApiDetails, ApiEndpoint, ServiceEndpointUsage
from atlas_plugin_apis.openapi_import import (
    SpecParseError,
    detect_spec_version,
    parse_operations,
    sync_endpoints_from_spec,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def system(group):
    return create_system(name="core", owner=group)


@pytest.fixture
def api(group, system):
    return create_api(
        name="billing-api", owner=group, system=system
    )  # default type='openapi'


OPENAPI_3X_SPEC = """
openapi: "3.0.0"
info: {title: Billing, version: "1.0"}
paths:
  /v1/invoices:
    get:
      operationId: listInvoices
      summary: List invoices
      tags: [invoices]
      parameters:
        - name: status
          in: query
          required: false
          schema: {type: string}
        - name: X-Trace-Id
          in: header
          required: false
          schema: {type: string}
        - name: session
          in: cookie
          schema: {type: string}
      responses:
        '200':
          description: OK
          content:
            application/json:
              schema:
                type: array
                items: {"$ref": "#/components/schemas/Invoice"}
    post:
      operationId: createInvoice
      requestBody:
        content:
          application/json:
            schema: {type: object, properties: {amount: {type: number}}}
            example: {amount: 10}
      responses:
        '201':
          description: Created
  /v1/invoices/{id}:
    get:
      operationId: getInvoice
      parameters:
        - name: id
          in: path
          required: true
          schema: {type: string}
      responses:
        '200': {description: OK}
components:
  schemas:
    Invoice:
      type: object
      properties:
        id: {type: string}
        total: {"$ref": "#/components/schemas/Money"}
    Money:
      type: object
      properties:
        amount: {type: number}
        currency: {type: string}
"""

SWAGGER_2_SPEC = """
swagger: "2.0"
info: {title: Billing, version: "1.0"}
produces: [application/json]
paths:
  /v1/invoices:
    post:
      operationId: createInvoiceLegacy
      consumes: [multipart/form-data]
      parameters:
        - name: amount
          in: formData
          type: number
          required: true
        - name: note
          in: formData
          type: string
      responses:
        '201':
          description: Created
    put:
      operationId: replaceInvoice
      parameters:
        - name: id
          in: path
          required: true
          type: string
        - name: notify
          in: query
          required: false
          type: boolean
        - name: X-Request-Id
          in: header
          required: false
          type: string
        - name: body
          in: body
          schema: {"$ref": "#/definitions/Invoice"}
      responses:
        '200':
          description: OK
          schema: {"$ref": "#/definitions/Invoice"}
definitions:
  Invoice:
    type: object
    properties:
      id: {type: string}
      amount: {type: number}
"""

SIMPLE_SPEC = """
openapi: "3.0.0"
paths:
  /v1/invoices:
    get:
      operationId: listInvoices
      summary: List invoices
      responses:
        '200': {description: OK}
"""

SIMPLE_SPEC_CHANGED = """
openapi: "3.0.0"
paths:
  /v1/invoices:
    get:
      operationId: listInvoices
      summary: List all invoices
      responses:
        '200': {description: OK}
"""

SIMPLE_SPEC_EMPTY_PATHS = """
openapi: "3.0.0"
paths: {}
"""


# --- Version detection (7.1) ----------------------------------------------


def test_detect_spec_version_recognizes_3x():
    assert detect_spec_version(OPENAPI_3X_SPEC) == openapi_import.VERSION_3X


def test_detect_spec_version_recognizes_2_0():
    assert detect_spec_version(SWAGGER_2_SPEC) == openapi_import.VERSION_2_0


def test_detect_spec_version_returns_none_for_unrecognized_document():
    assert detect_spec_version("foo: bar") is None


# --- 3.x parsing (7.1) ------------------------------------------------------


def test_parses_3x_request_body_into_body_shape():
    operations = parse_operations(OPENAPI_3X_SPEC)
    create_op = next(op for op in operations if op.method == "POST")

    assert create_op.request["body"] == {
        "content_type": "application/json",
        "schema": {"type": "object", "properties": {"amount": {"type": "number"}}},
        "example": {"amount": 10},
    }


def test_3x_request_body_ref_schema_is_resolved():
    spec = """
openapi: "3.0.0"
paths:
  /v1/invoices:
    post:
      operationId: createInvoice
      requestBody:
        content:
          application/json:
            schema: {"$ref": "#/components/schemas/CreateInvoiceRequest"}
      responses:
        '201':
          description: Created
components:
  schemas:
    CreateInvoiceRequest:
      type: object
      properties:
        amount: {type: number}
"""
    [op] = parse_operations(spec)

    assert op.request["body"] == {
        "content_type": "application/json",
        "schema": {"type": "object", "properties": {"amount": {"type": "number"}}},
        "example": None,
    }


def test_cookie_parameter_is_dropped_without_failing_the_operation():
    operations = parse_operations(OPENAPI_3X_SPEC)
    list_op = next(
        op for op in operations if op.method == "GET" and op.path == "/v1/invoices"
    )

    locations = {param["location"] for param in list_op.request["parameters"]}
    names = {param["name"] for param in list_op.request["parameters"]}
    assert "cookie" not in locations
    assert names == {"status", "X-Trace-Id"}


def test_3x_query_and_header_parameters_are_mapped():
    operations = parse_operations(OPENAPI_3X_SPEC)
    list_op = next(
        op for op in operations if op.method == "GET" and op.path == "/v1/invoices"
    )

    by_name = {param["name"]: param for param in list_op.request["parameters"]}
    assert by_name["status"]["location"] == "query"
    assert by_name["X-Trace-Id"]["location"] == "header"


def test_3x_path_parameter_is_mapped():
    operations = parse_operations(OPENAPI_3X_SPEC)
    get_op = next(op for op in operations if op.path == "/v1/invoices/{id}")

    [param] = get_op.request["parameters"]
    assert param == {
        "name": "id",
        "location": "path",
        "required": True,
        "description": "",
        "schema": {"type": "string"},
    }


def test_ref_schema_is_resolved_to_expanded_content():
    operations = parse_operations(OPENAPI_3X_SPEC)
    list_op = next(
        op for op in operations if op.method == "GET" and op.path == "/v1/invoices"
    )
    [response] = [r for r in list_op.responses if r["status_code"] == "200"]

    assert response["schema"] == {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "total": {
                    "type": "object",
                    "properties": {
                        "amount": {"type": "number"},
                        "currency": {"type": "string"},
                    },
                },
            },
        },
    }


def test_nested_property_ref_inside_an_otherwise_inline_schema_resolves():
    operations = parse_operations(OPENAPI_3X_SPEC)
    list_op = next(
        op for op in operations if op.method == "GET" and op.path == "/v1/invoices"
    )
    [response] = [r for r in list_op.responses if r["status_code"] == "200"]

    assert response["schema"]["items"]["properties"]["total"] == {
        "type": "object",
        "properties": {"amount": {"type": "number"}, "currency": {"type": "string"}},
    }


# --- 2.0 parsing (7.1) -------------------------------------------------------


def test_swagger2_formdata_parameters_become_one_object_body_schema():
    operations = parse_operations(SWAGGER_2_SPEC)
    create_op = next(op for op in operations if op.method == "POST")

    assert create_op.request["body"] == {
        "content_type": "multipart/form-data",
        "schema": {
            "type": "object",
            "properties": {"amount": {"type": "number"}, "note": {"type": "string"}},
            "required": ["amount"],
        },
        "example": None,
    }


def test_swagger2_body_parameter_maps_with_document_consumes_default_and_resolves_schema():
    operations = parse_operations(SWAGGER_2_SPEC)
    put_op = next(op for op in operations if op.method == "PUT")

    assert put_op.request["body"] == {
        "content_type": "application/json",
        "schema": {
            "type": "object",
            "properties": {"id": {"type": "string"}, "amount": {"type": "number"}},
        },
        "example": None,
    }


def test_swagger2_path_query_header_parameters_are_mapped():
    operations = parse_operations(SWAGGER_2_SPEC)
    put_op = next(op for op in operations if op.method == "PUT")

    by_name = {param["name"]: param for param in put_op.request["parameters"]}
    assert by_name["id"] == {
        "name": "id",
        "location": "path",
        "required": True,
        "description": "",
        "schema": {"type": "string"},
    }
    assert by_name["notify"]["location"] == "query"
    assert by_name["X-Request-Id"]["location"] == "header"


def test_swagger2_response_schema_uses_produces_content_type_and_resolves_against_definitions():
    operations = parse_operations(SWAGGER_2_SPEC)
    put_op = next(op for op in operations if op.method == "PUT")

    [response] = put_op.responses
    assert response["content_type"] == "application/json"
    assert response["schema"] == {
        "type": "object",
        "properties": {"id": {"type": "string"}, "amount": {"type": "number"}},
    }


# --- Response headers ------------


def test_3x_response_headers_are_imported():
    spec = """
openapi: "3.0.0"
paths:
  /v1/invoices:
    get:
      operationId: listInvoices
      responses:
        '200':
          description: OK
          headers:
            X-Rate-Limit:
              description: Requests remaining
              schema: {type: integer}
"""
    [op] = parse_operations(spec)
    [response] = op.responses

    assert response["headers"] == {
        "X-Rate-Limit": {
            "description": "Requests remaining",
            "schema": {"type": "integer"},
        },
    }


def test_2x_response_headers_are_imported():
    spec = """
swagger: "2.0"
paths:
  /v1/invoices:
    get:
      operationId: listInvoices
      produces: [application/json]
      responses:
        '200':
          description: OK
          schema: {type: object}
          headers:
            X-Rate-Limit:
              description: Requests remaining
              type: integer
"""
    [op] = parse_operations(spec)
    [response] = op.responses

    assert response["headers"] == {
        "X-Rate-Limit": {
            "description": "Requests remaining",
            "schema": {"type": "integer"},
        },
    }


def test_response_with_no_headers_has_no_headers_key():
    operations = parse_operations(OPENAPI_3X_SPEC)
    list_op = next(
        op for op in operations if op.method == "GET" and op.path == "/v1/invoices"
    )
    [response] = [r for r in list_op.responses if r["status_code"] == "200"]

    assert "headers" not in response


# --- Operation externalDocs ------


def test_3x_operation_external_docs_is_imported():
    spec = """
openapi: "3.0.0"
paths:
  /v1/invoices:
    get:
      operationId: listInvoices
      externalDocs:
        description: More info
        url: https://example.com/docs
      responses:
        '200': {description: OK}
"""
    [op] = parse_operations(spec)

    assert op.external_docs == {
        "description": "More info",
        "url": "https://example.com/docs",
    }


def test_2x_operation_external_docs_is_imported():
    spec = """
swagger: "2.0"
paths:
  /v1/invoices:
    get:
      operationId: listInvoices
      externalDocs:
        url: https://example.com/docs
      responses:
        '200': {description: OK}
"""
    [op] = parse_operations(spec)

    assert op.external_docs == {"description": "", "url": "https://example.com/docs"}


def test_operation_with_no_external_docs_yields_empty_dict():
    operations = parse_operations(SIMPLE_SPEC)
    [op] = operations

    assert op.external_docs == {}


# --- Operation security resolution -


def test_3x_security_resolves_against_security_schemes():
    spec = """
openapi: "3.0.0"
paths:
  /v1/invoices:
    get:
      operationId: listInvoices
      security:
        - BearerAuth: []
      responses:
        '200': {description: OK}
components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
"""
    [op] = parse_operations(spec)

    assert op.security == [{"type": "http", "scheme": "bearer"}]


def test_2x_security_resolves_against_security_definitions():
    spec = """
swagger: "2.0"
paths:
  /v1/invoices:
    get:
      operationId: listInvoices
      security:
        - ApiKeyAuth: []
      responses:
        '200': {description: OK}
securityDefinitions:
  ApiKeyAuth:
    type: apiKey
    name: X-API-Key
    in: header
"""
    [op] = parse_operations(spec)

    assert op.security == [{"type": "apiKey", "scheme": None}]


def test_operation_without_own_security_inherits_document_level_requirement():
    spec = """
openapi: "3.0.0"
security:
  - BearerAuth: []
paths:
  /v1/invoices:
    get:
      operationId: listInvoices
      responses:
        '200': {description: OK}
components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
"""
    [op] = parse_operations(spec)

    assert op.security == [{"type": "http", "scheme": "bearer"}]


def test_operations_own_empty_security_overrides_the_document_level_requirement():
    spec = """
openapi: "3.0.0"
security:
  - BearerAuth: []
paths:
  /v1/invoices:
    get:
      operationId: listInvoices
      security: []
      responses:
        '200': {description: OK}
components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
"""
    [op] = parse_operations(spec)

    assert op.security == []


def test_security_requirement_referencing_an_unknown_scheme_is_dropped():
    spec = """
openapi: "3.0.0"
paths:
  /v1/invoices:
    get:
      operationId: listInvoices
      security:
        - UnknownScheme: []
        - BearerAuth: []
      responses:
        '200': {description: OK}
components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
"""
    [op] = parse_operations(spec)

    assert op.security == [{"type": "http", "scheme": "bearer"}]


def test_security_requirement_referencing_only_unknown_schemes_yields_empty_list():
    spec = """
openapi: "3.0.0"
paths:
  /v1/invoices:
    get:
      operationId: listInvoices
      security:
        - UnknownScheme: []
      responses:
        '200': {description: OK}
"""
    [op] = parse_operations(spec)

    assert op.security == []


def test_synced_endpoint_stores_headers_external_docs_and_security(api):
    spec = """
openapi: "3.0.0"
paths:
  /v1/invoices:
    get:
      operationId: listInvoices
      externalDocs:
        description: More info
        url: https://example.com/docs
      security:
        - BearerAuth: []
      responses:
        '200':
          description: OK
          headers:
            X-Rate-Limit:
              description: Requests remaining
              schema: {type: integer}
components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
"""
    details = api.api_details
    details.spec_content = spec

    sync_endpoints_from_spec(details)

    endpoint = ApiEndpoint.objects.get(
        api=api, method=ApiEndpoint.METHOD_GET, path="/v1/invoices"
    )
    assert endpoint.external_docs == {
        "description": "More info",
        "url": "https://example.com/docs",
    }
    assert endpoint.security == [{"type": "http", "scheme": "bearer"}]
    assert endpoint.responses[0]["headers"] == {
        "X-Rate-Limit": {
            "description": "Requests remaining",
            "schema": {"type": "integer"},
        },
    }


# --- $ref resolution: cycle safety / sibling merging --


SELF_REFERENTIAL_SPEC = """
openapi: "3.0.0"
paths:
  /v1/categories:
    get:
      operationId: listCategories
      responses:
        '200':
          description: OK
          content:
            application/json:
              schema: {"$ref": "#/components/schemas/Category"}
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


def test_self_referential_schema_syncs_successfully_without_looping(api):
    details = api.api_details
    details.spec_content = SELF_REFERENTIAL_SPEC

    sync_endpoints_from_spec(details)

    details.refresh_from_db()
    assert details.endpoints_sync_failed is False
    endpoint = ApiEndpoint.objects.get(
        api=api, method=ApiEndpoint.METHOD_GET, path="/v1/categories"
    )
    [response] = endpoint.responses
    assert response["schema"]["properties"]["children"]["items"] == {
        "$ref": "#/components/schemas/Category"
    }


def test_sibling_key_next_to_a_ref_is_merged_onto_the_resolved_schema():
    spec = """
openapi: "3.0.0"
paths:
  /v1/invoices:
    get:
      operationId: listInvoices
      responses:
        '200':
          description: OK
          content:
            application/json:
              schema: {"$ref": "#/components/schemas/Invoice", "description": "override"}
components:
  schemas:
    Invoice:
      type: object
      properties:
        id: {type: string}
"""
    [op] = parse_operations(spec)
    [response] = op.responses

    assert response["schema"] == {
        "type": "object",
        "properties": {"id": {"type": "string"}},
        "description": "override",
    }


def test_sibling_key_survives_a_dangling_ref():
    spec = """
openapi: "3.0.0"
paths:
  /v1/invoices:
    get:
      operationId: listInvoices
      responses:
        '200':
          description: OK
          content:
            application/json:
              schema: {"$ref": "#/components/schemas/Missing", "description": "override"}
"""
    [op] = parse_operations(spec)
    [response] = op.responses

    assert response["schema"] == {
        "$ref": "#/components/schemas/Missing",
        "description": "override",
    }


def test_one_malformed_operation_is_skipped_and_logged_without_aborting_the_parse(
    caplog,
):
    spec = """
openapi: "3.0.0"
paths:
  /v1/good:
    get:
      operationId: good
      responses:
        '200': {description: OK}
  /v1/bad:
    get:
      operationId: bad
      parameters: 5
      responses:
        '200': {description: OK}
"""
    operations = parse_operations(spec, api_label="billing-api")

    assert [op.path for op in operations] == ["/v1/good"]
    assert "billing-api" in caplog.text


# --- Spec-level parse failures (7.1/7.3) -------------------------------------


def test_parse_operations_raises_for_unrecognized_version():
    with pytest.raises(SpecParseError):
        parse_operations("foo: bar")


def test_parse_operations_raises_for_missing_paths():
    with pytest.raises(SpecParseError):
        parse_operations('openapi: "3.0.0"\ninfo: {}\n')


def test_parse_operations_raises_for_invalid_yaml():
    with pytest.raises(SpecParseError):
        parse_operations("not: yaml: [unterminated")


# --- servers -> base URL/protocol resolution --


def _resolve_servers(spec_content: str, version: str) -> tuple[str, str]:
    return openapi_import._resolve_servers(yaml.safe_load(spec_content), version)


def test_single_3x_server_resolves_base_url_and_protocol():
    spec = """
openapi: "3.0.0"
servers:
  - url: https://api.example.com/v1
paths: {}
"""
    base_url, protocol = _resolve_servers(spec, openapi_import.VERSION_3X)

    assert base_url == "https://api.example.com/v1"
    assert protocol == "https"


def test_multiple_3x_servers_leave_base_url_and_protocol_unresolved():
    spec = """
openapi: "3.0.0"
servers:
  - url: https://prod.example.com/v1
  - url: https://staging.example.com/v1
paths: {}
"""
    base_url, protocol = _resolve_servers(spec, openapi_import.VERSION_3X)

    assert (base_url, protocol) == ("", "")


def test_no_3x_servers_leaves_base_url_and_protocol_unresolved():
    spec = """
openapi: "3.0.0"
paths: {}
"""
    base_url, protocol = _resolve_servers(spec, openapi_import.VERSION_3X)

    assert (base_url, protocol) == ("", "")


def test_2x_single_scheme_resolves_base_url_and_protocol():
    spec = """
swagger: "2.0"
host: api.example.com
basePath: /v1
schemes: [https]
paths: {}
"""
    base_url, protocol = _resolve_servers(spec, openapi_import.VERSION_2_0)

    assert base_url == "api.example.com/v1"
    assert protocol == "https"


def test_2x_multiple_schemes_resolve_base_url_only():
    spec = """
swagger: "2.0"
host: api.example.com
basePath: /v1
schemes: [http, https]
paths: {}
"""
    base_url, protocol = _resolve_servers(spec, openapi_import.VERSION_2_0)

    assert base_url == "api.example.com/v1"
    assert protocol == ""


def test_2x_missing_host_leaves_base_url_and_protocol_unresolved():
    spec = """
swagger: "2.0"
paths: {}
"""
    base_url, protocol = _resolve_servers(spec, openapi_import.VERSION_2_0)

    assert (base_url, protocol) == ("", "")


def test_sync_persists_resolved_base_url_and_protocol_for_a_single_server(api):
    spec = """
openapi: "3.0.0"
servers:
  - url: https://api.example.com/v1
paths:
  /v1/invoices:
    get:
      operationId: listInvoices
      responses:
        '200': {description: OK}
"""
    details = api.api_details
    details.spec_content = spec

    sync_endpoints_from_spec(details)

    details.refresh_from_db()
    assert details.resolved_base_url == "https://api.example.com/v1"
    assert details.resolved_protocol == "https"


def test_sync_leaves_resolved_base_url_and_protocol_empty_for_multiple_servers(api):
    spec = """
openapi: "3.0.0"
servers:
  - url: https://prod.example.com/v1
  - url: https://staging.example.com/v1
paths:
  /v1/invoices:
    get:
      operationId: listInvoices
      responses:
        '200': {description: OK}
"""
    details = api.api_details
    details.spec_content = spec

    sync_endpoints_from_spec(details)

    details.refresh_from_db()
    assert details.resolved_base_url == ""
    assert details.resolved_protocol == ""


# --- Upsert / lifecycle (7.2) ------------------------------------------------


def test_new_operation_creates_an_endpoint(api):
    details = api.api_details
    details.spec_content = SIMPLE_SPEC

    sync_endpoints_from_spec(details)

    endpoint = ApiEndpoint.objects.get(
        api=api, method=ApiEndpoint.METHOD_GET, path="/v1/invoices"
    )
    assert endpoint.status == ApiEndpoint.STATUS_ACTIVE
    assert endpoint.summary == "List invoices"
    assert endpoint.operation_id == "listInvoices"


def test_changed_operation_updates_fields_and_preserves_id(api):
    details = api.api_details
    details.spec_content = SIMPLE_SPEC
    sync_endpoints_from_spec(details)
    endpoint = ApiEndpoint.objects.get(
        api=api, method=ApiEndpoint.METHOD_GET, path="/v1/invoices"
    )
    original_id = endpoint.id

    details.spec_content = SIMPLE_SPEC_CHANGED
    sync_endpoints_from_spec(details)

    endpoint.refresh_from_db()
    assert endpoint.id == original_id
    assert endpoint.summary == "List all invoices"


def test_operation_missing_from_reparse_soft_removes_and_preserves_service_links(
    api, group, system
):
    details = api.api_details
    details.spec_content = SIMPLE_SPEC
    sync_endpoints_from_spec(details)
    endpoint = ApiEndpoint.objects.get(
        api=api, method=ApiEndpoint.METHOD_GET, path="/v1/invoices"
    )
    service = create_component(name="billing-service", owner=group, system=system)
    usage = ServiceEndpointUsage.objects.create(endpoint=endpoint, service=service)

    details.spec_content = SIMPLE_SPEC_EMPTY_PATHS
    sync_endpoints_from_spec(details)

    endpoint.refresh_from_db()
    assert endpoint.status == ApiEndpoint.STATUS_REMOVED
    assert ApiEndpoint.objects.filter(pk=endpoint.pk).exists()
    assert ServiceEndpointUsage.objects.filter(pk=usage.pk).exists()


def test_removed_operation_reappearing_revives_with_updated_fields_and_preserved_links(
    api, group, system
):
    details = api.api_details
    details.spec_content = SIMPLE_SPEC
    sync_endpoints_from_spec(details)
    endpoint = ApiEndpoint.objects.get(
        api=api, method=ApiEndpoint.METHOD_GET, path="/v1/invoices"
    )
    original_id = endpoint.id
    service = create_component(name="billing-service", owner=group, system=system)
    usage = ServiceEndpointUsage.objects.create(endpoint=endpoint, service=service)

    details.spec_content = SIMPLE_SPEC_EMPTY_PATHS
    sync_endpoints_from_spec(details)
    endpoint.refresh_from_db()
    assert endpoint.status == ApiEndpoint.STATUS_REMOVED

    details.spec_content = SIMPLE_SPEC_CHANGED
    sync_endpoints_from_spec(details)

    endpoint.refresh_from_db()
    assert endpoint.status == ApiEndpoint.STATUS_ACTIVE
    assert endpoint.id == original_id
    assert endpoint.summary == "List all invoices"
    assert ServiceEndpointUsage.objects.filter(pk=usage.pk).exists()


# --- Failure paths (7.3) ------------------------------------------------------


def test_unparseable_spec_sets_failure_flag_and_leaves_existing_endpoints_untouched(
    api,
):
    details = api.api_details
    details.spec_content = SIMPLE_SPEC
    sync_endpoints_from_spec(details)
    endpoint = ApiEndpoint.objects.get(
        api=api, method=ApiEndpoint.METHOD_GET, path="/v1/invoices"
    )

    details.spec_content = "not: yaml: [unterminated"
    sync_endpoints_from_spec(details)

    details.refresh_from_db()
    assert details.endpoints_sync_failed is True
    endpoint.refresh_from_db()
    assert endpoint.status == ApiEndpoint.STATUS_ACTIVE
    assert endpoint.summary == "List invoices"


def test_one_malformed_operation_among_valid_ones_imports_the_rest_without_flagging_failure(
    api,
):
    spec = """
openapi: "3.0.0"
paths:
  /v1/good:
    get:
      operationId: good
      responses:
        '200': {description: OK}
  /v1/bad:
    get:
      operationId: bad
      parameters: 5
      responses:
        '200': {description: OK}
"""
    details = api.api_details
    details.spec_content = spec

    sync_endpoints_from_spec(details)

    details.refresh_from_db()
    assert details.endpoints_sync_failed is False
    assert ApiEndpoint.objects.filter(api=api, path="/v1/good").exists()
    assert not ApiEndpoint.objects.filter(api=api, path="/v1/bad").exists()


def test_successful_sync_clears_a_prior_failure_and_updates_timestamp(api):
    details = api.api_details
    details.spec_content = "not: yaml: [unterminated"
    sync_endpoints_from_spec(details)
    details.refresh_from_db()
    assert details.endpoints_sync_failed is True
    assert details.endpoints_synced_at is None

    details.spec_content = SIMPLE_SPEC
    sync_endpoints_from_spec(details)

    details.refresh_from_db()
    assert details.endpoints_sync_failed is False
    assert details.endpoints_synced_at is not None


def test_non_openapi_typed_api_is_never_synced(group, system):
    entity = create_api(
        name="grpc-api", owner=group, system=system, type=ApiDetails.TYPE_GRPC
    )
    details = entity.api_details
    details.spec_content = "service Foo {}"

    sync_endpoints_from_spec(details)

    assert not ApiEndpoint.objects.filter(api=entity).exists()
    details.refresh_from_db()
    assert details.endpoints_synced_at is None


def test_empty_spec_content_is_never_synced(api):
    details = api.api_details
    details.spec_content = ""

    sync_endpoints_from_spec(details)

    assert not ApiEndpoint.objects.filter(api=api).exists()
    details.refresh_from_db()
    assert details.endpoints_synced_at is None


# --- Periodic refresh write path (4.4/7.4) -----------------------------------
#
# `atlas_plugin_ingestion.pipeline.refresh_spec_urls` is a thin wrapper around
# `due_for_spec_refresh` (extension_points.py docstring), so exercising the
# latter directly here covers that write path without this plugin's tests
# needing to import `atlas_plugin_ingestion` (no such dependency exists today).


SPEC_FETCH_PATCH_TARGET = "atlas_plugin_apis.spec_fetch.safe_request"


def test_due_for_spec_refresh_syncs_endpoints_from_the_newly_fetched_spec(api):
    details = api.api_details
    details.spec_source = ApiDetails.SPEC_SOURCE_URL
    details.spec_url = "https://example.com/openapi.yaml"
    details.save()

    with patch(SPEC_FETCH_PATCH_TARGET) as mock_get:
        mock_get.return_value = SafeHttpResponse(
            status_code=200,
            headers={},
            url="https://example.com/openapi.yaml",
            resolved_address="203.0.113.1",
            content=SIMPLE_SPEC.encode(),
        )
        due_for_spec_refresh()

    endpoint = ApiEndpoint.objects.get(
        api=api, method=ApiEndpoint.METHOD_GET, path="/v1/invoices"
    )
    assert endpoint.operation_id == "listInvoices"
    details.refresh_from_db()
    assert details.endpoints_sync_failed is False
    assert details.endpoints_synced_at is not None


# --- Signal wiring / re-entrancy regression (4.1/4.2, 7.5) -------------------


def test_post_save_receiver_skips_sync_for_saves_scoped_to_sync_status_fields(api):
    details = api.api_details

    with patch(
        "atlas_plugin_apis.openapi_import.sync_endpoints_from_spec"
    ) as mock_sync:
        signals_module._sync_endpoints_on_save(
            ApiDetails,
            details,
            update_fields=frozenset({"endpoints_synced_at", "endpoints_sync_failed"}),
        )
        mock_sync.assert_not_called()

        signals_module._sync_endpoints_on_save(
            ApiDetails, details, update_fields=frozenset({"spec_content"})
        )
        mock_sync.assert_called_once_with(details)

        signals_module._sync_endpoints_on_save(ApiDetails, details, update_fields=None)
        assert mock_sync.call_count == 2


def test_self_save_after_a_sync_does_not_retrigger_a_second_sync_pass(api):
    details = api.api_details
    details.spec_content = SIMPLE_SPEC

    with patch(
        "atlas_plugin_apis.openapi_import.parse_operations",
        wraps=openapi_import.parse_operations,
    ) as parse_spy:
        details.save(update_fields=["spec_content"])

    assert parse_spy.call_count == 1
    details.refresh_from_db()
    assert details.endpoints_sync_failed is False
    assert details.endpoints_synced_at is not None
    assert ApiEndpoint.objects.filter(api=api, path="/v1/invoices").exists()
