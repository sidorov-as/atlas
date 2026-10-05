"""Flows record creation and modification times (`flows-plugin` spec: "Flows record creation
and modification times")."""

import pytest
from django.contrib import admin
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from atlas_plugin_flows.models import Flow

BEFORE = ("catalog", "0002_seed_catalog_home_settings")
AFTER = ("catalog", "0003_flow_timestamps")


def test_new_flow_has_both_times(system):
    flow = Flow.objects.create(system=system, name="checkout")

    assert flow.created_at is not None
    assert flow.updated_at is not None


def test_edit_updates_modification_time_only(system):
    flow = Flow.objects.create(system=system, name="checkout")
    created_at, updated_at = flow.created_at, flow.updated_at

    flow.name = "checkout-v2"
    flow.save()
    flow.refresh_from_db()

    assert flow.created_at == created_at
    assert flow.updated_at > updated_at


def test_admin_shows_times_read_only():
    flow_admin = admin.site._registry[Flow]

    assert {"created_at", "updated_at"} <= set(flow_admin.readonly_fields)


@pytest.mark.django_db(transaction=True)
def test_existing_flows_get_times_at_migration(system):
    executor = MigrationExecutor(connection)
    executor.migrate([BEFORE])
    try:
        old_flow = executor.loader.project_state([BEFORE]).apps.get_model(
            "catalog", "Flow"
        )
        legacy_id = old_flow.objects.create(system_id=system.pk, name="legacy").pk

        executor = MigrationExecutor(connection)
        executor.migrate([AFTER])
        new_flow = executor.loader.project_state([AFTER]).apps.get_model(
            "catalog", "Flow"
        )

        migrated = new_flow.objects.get(pk=legacy_id)
        assert migrated.created_at is not None
        assert migrated.updated_at is not None
    finally:
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
