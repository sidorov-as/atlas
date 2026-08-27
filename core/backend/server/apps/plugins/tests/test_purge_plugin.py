"""`purge_plugin` management command."""

import io

import pytest
from atlas_plugin_database_schema.models import DatabaseSchema
from atlas_plugin_standard_catalog.models import ResourceDetails
from django.core.management import CommandError, call_command

from server.apps.catalog.models import KIND_RESOURCE, CatalogEntity

pytestmark = pytest.mark.django_db


@pytest.fixture
def resource_with_schema(group):
    entity = CatalogEntity.objects.create(
        kind=KIND_RESOURCE,
        name="primary-db",
        owner=group,
    )
    ResourceDetails.objects.create(entity=entity, type="database")
    DatabaseSchema.objects.create(
        entity=entity,
        source_sql="CREATE TABLE t (id int);",
    )
    return entity


def _call(*args):
    out = io.StringIO()
    call_command("purge_plugin", *args, stdout=out)
    return out.getvalue()


def test_dry_run_reports_scope_without_deleting(resource_with_schema):
    output = _call("atlas.database-schema")

    assert "database_schema" in output.lower()
    assert "1 row" in output
    assert "Dry run only" in output
    assert DatabaseSchema.objects.count() == 1


def test_confirm_deletes_data_but_not_the_underlying_resource(
    resource_with_schema,
):
    output = _call("atlas.database-schema", "--confirm")

    assert "Purged" in output
    assert DatabaseSchema.objects.count() == 0
    assert CatalogEntity.objects.filter(id=resource_with_schema.id).exists()
    assert ResourceDetails.objects.filter(
        entity_id=resource_with_schema.id,
    ).exists()


def test_rejects_a_plugin_whose_code_is_not_installed():
    with pytest.raises(CommandError, match="not among the selected plugins"):
        _call("atlas.not-a-real-plugin")
