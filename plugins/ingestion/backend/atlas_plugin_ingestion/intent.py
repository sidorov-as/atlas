"""`EntityIntent` — the value type ingestion submits to the core Entity
Service.

Constructed after a manifest document has been schema-validated (`validation.
validate_manifest_document`) and arbitration has cleared the claim — a
rejected claim never reaches this point — and
is only then passed to `EntityService.create`/`.update`. `EntityService` never
needs arbitration-awareness: by the time it sees an `EntityIntent`, ingestion
has already decided the write is allowed.
"""

from dataclasses import dataclass

from atlas_plugin_api import SOURCE_YAML
from pydantic import BaseModel

from .models import RegisteredRepository


@dataclass(frozen=True)
class EntityIntent:
    kind: str
    """Entity Kind registry id (e.g. `'system'`) — not the manifest's own
    `kind` field (e.g. `'System'`), so this maps directly onto
    `EntityService.create`/`.update`'s `kind_id`."""

    namespace: str
    name: str
    metadata: BaseModel
    spec: BaseModel
    ingested_from: RegisteredRepository
    source_kind: str = SOURCE_YAML
