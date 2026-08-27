"""Pre-create the owner Groups the fixture manifests reference (`catalog-info.yaml`
cannot declare `kind: Group`) and register the fixture repositories against
the `gitea-primary` ingestion source."""

from atlas_plugin_api import KIND_GROUP, get_catalog_entity_model
from atlas_plugin_ingestion.models import RegisteredRepository
from atlas_plugin_standard_catalog.models import GroupDetails

Entity = get_catalog_entity_model()

for group_name in ('search-team', 'booking-team', 'payments-team'):
    entity, _ = Entity.objects.get_or_create(kind=KIND_GROUP, name=group_name)
    GroupDetails.objects.update_or_create(entity=entity, defaults={'type': 'team'})

for repo_path in (
    'atlas-demo/search-discovery',
    'atlas-demo/payments-payouts',
    'atlas-demo/booking-reservations',
):
    RegisteredRepository.objects.update_or_create(
        source_id='gitea-primary',
        path=repo_path,
        defaults={'default_branch': 'main'},
    )
