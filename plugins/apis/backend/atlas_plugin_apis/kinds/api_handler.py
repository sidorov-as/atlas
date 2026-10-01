"""`api` Entity Kind handler — split out of
`server.apps.catalog.kinds.api_handler`.

Owns the synchronous `spec_url` resolution on create/update, sharing `spec_fetch.apply_api_spec_source` with ingestion's periodic
refresh.
"""

from typing import ClassVar

from atlas_plugin_api import (
    KIND_API,
    KIND_SYSTEM,
    CatalogEntity,
    refs,
)
from pydantic import BaseModel

from ..api.schemas import ApiSpecIn, ApiSpecOut, ApiSpecPatch
from ..extension_points import run_delete_guards
from ..models import ApiDetails
from ..spec_fetch import apply_api_spec_source


class ApiKindHandler:
    kind_id = KIND_API
    spec_schema: type[BaseModel] = ApiSpecIn
    patch_schema: type[BaseModel] = ApiSpecPatch
    # APIs can appear inside C4 diagrams (an optional atlas.apis
    # dependency) but aren't themselves a diagram subject yet — declares no
    # capability.
    provides: ClassVar[list] = []

    def create_details(self, entity: CatalogEntity, spec: ApiSpecIn) -> None:
        details = ApiDetails(
            entity=entity,
            type=spec.type,
            system=refs.resolve_ref(spec.system, expected_kind=KIND_SYSTEM),
        )
        apply_api_spec_source(
            details, spec.spec_source, spec.spec_url, spec.spec_content
        )
        details.save()

    def update_details(self, entity: CatalogEntity, spec: ApiSpecPatch) -> None:
        details = entity.api_details
        fields = spec.model_fields_set
        if "type" in fields:
            details.type = spec.type
        if "system" in fields:
            details.system = refs.resolve_ref(spec.system, expected_kind=KIND_SYSTEM)
        if fields & {"spec_source", "spec_url", "spec_content"}:
            spec_source = (
                spec.spec_source if "spec_source" in fields else details.spec_source
            )
            spec_url = spec.spec_url if "spec_url" in fields else details.spec_url
            spec_content = (
                spec.spec_content if "spec_content" in fields else details.spec_content
            )
            apply_api_spec_source(details, spec_source, spec_url, spec_content)
        details.save()

    def serialize_details(self, entity: CatalogEntity) -> BaseModel:
        details = entity.api_details
        return ApiSpecOut(
            type=details.type,
            owner=entity.owner.ref,
            owner_id=entity.owner_id,
            system=details.system.ref,
            system_id=details.system_id,
            spec_source=details.spec_source,
            spec_url=details.spec_url,
            spec_content=details.spec_content,
            spec_resolved_at=details.spec_resolved_at,
            spec_resolve_failed=details.spec_resolve_failed,
            endpoints_synced_at=details.endpoints_synced_at,
            endpoints_sync_failed=details.endpoints_sync_failed,
            operations_synced_at=details.operations_synced_at,
            operations_sync_failed=details.operations_sync_failed,
        )

    def validate_delete(self, entity: CatalogEntity) -> None:
        # Runs every registered delete guard (extension_points.py) —
        # `atlas_plugin_standard_catalog`'s guard checks
        # `ComponentDetails.provides_apis`/`consumes_apis` (plain M2Ms, not
        # PROTECTed by the DB), the only check standing between a delete and
        # silently orphaning dependent Components — without this handler
        # importing that plugin's models directly.
        run_delete_guards(entity)

    def is_deprecated(self, entity: CatalogEntity) -> bool:
        # A whole `api` entity carries no cosmetic lifecycle flag of its own —
        # only its individual Endpoints/Operations do.
        return False
