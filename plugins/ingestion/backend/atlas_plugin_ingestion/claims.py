"""Entity claims: which repository owns a catalog entity.

Written by ingestion's own upsert, and by core's adopt action (through
`server.apps.catalog.api.helpers`, which imports this module lazily when
ingestion is active).
"""

from .models import EntityClaim, RegisteredRepository


def claim_entity(entity, repository: RegisteredRepository) -> EntityClaim:
    """Record that `repository` claims `entity`, replacing any prior claim."""
    claim, _created = EntityClaim.objects.update_or_create(
        entity=entity,
        defaults={"repository": repository},
    )
    return claim


def claiming_repository_id(entity) -> int | None:
    """Id of the repository claiming `entity`, or `None` if unclaimed."""
    return (
        EntityClaim.objects.filter(entity=entity)
        .values_list("repository_id", flat=True)
        .first()
    )
