"""Rows that exist before `0006_usage_origin_and_source` are backfilled
with `origin=manual` and `source=ui` (`endpoint-service-dependencies` /
`operation-service-dependencies` specs: "Pre-existing links are migrated")."""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from server.apps.catalog.tests.factories import (
    create_api,
    create_component,
    create_group,
    create_system,
)

BEFORE = ("apis_plugin", "0005_apiendpoint_external_docs_apiendpoint_security")
AFTER = ("apis_plugin", "0006_usage_origin_and_source")


@pytest.mark.django_db(transaction=True)
def test_existing_usage_rows_are_backfilled_as_manual_ui():
    executor = MigrationExecutor(connection)
    executor.migrate([BEFORE])
    try:
        old_apps = executor.loader.project_state([BEFORE]).apps
        Endpoint = old_apps.get_model("apis_plugin", "ApiEndpoint")
        Operation = old_apps.get_model("apis_plugin", "ApiOperation")
        EndpointUsage = old_apps.get_model("apis_plugin", "ServiceEndpointUsage")
        OperationUsage = old_apps.get_model("apis_plugin", "ServiceOperationUsage")
        group = create_group(name="legacy-team")
        system = create_system(name="legacy-system", owner=group)
        api = create_api(name="legacy-api", owner=group, system=system)
        service = create_component(name="legacy-service", owner=group, system=system)
        endpoint = Endpoint.objects.create(api_id=api.pk, method="GET", path="/x")
        operation = Operation.objects.create(
            api_id=api.pk,
            channel_address="orders",
            direction="send",
            operation_key="k",
        )
        endpoint_usage = EndpointUsage.objects.create(
            endpoint_id=endpoint.pk, service_id=service.pk
        )
        operation_usage = OperationUsage.objects.create(
            operation_id=operation.pk, service_id=service.pk, role="publisher"
        )

        executor = MigrationExecutor(connection)
        executor.migrate([AFTER])
        new_apps = executor.loader.project_state([AFTER]).apps

        migrated_endpoint = new_apps.get_model(
            "apis_plugin", "ServiceEndpointUsage"
        ).objects.get(pk=endpoint_usage.pk)
        migrated_operation = new_apps.get_model(
            "apis_plugin", "ServiceOperationUsage"
        ).objects.get(pk=operation_usage.pk)
        for row in (migrated_endpoint, migrated_operation):
            assert (row.origin, row.source) == ("manual", "ui")
    finally:
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
