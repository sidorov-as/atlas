"""Create Atlas-side targets and the disposable local fallback account."""

import os

from atlas_plugin_api import KIND_ACTOR, KIND_GROUP, get_catalog_entity_model
from atlas_plugin_standard_catalog.models import ActorDetails, GroupDetails
from django.contrib.auth import get_user_model

Entity = get_catalog_entity_model()

group_entity, _ = Entity.objects.get_or_create(
    kind=KIND_GROUP,
    name="custom-platform",
)
GroupDetails.objects.update_or_create(
    entity=group_entity,
    defaults={"type": "team"},
)

username = os.environ["ATLAS_LOCAL_FALLBACK_USERNAME"]
user, _ = get_user_model().objects.get_or_create(username=username)
user.is_active = True
user.is_staff = False
user.is_superuser = False
user.set_password(os.environ["ATLAS_LOCAL_FALLBACK_PASSWORD"])
user.save()

actor_entity, _ = Entity.objects.get_or_create(kind=KIND_ACTOR, name=username)
ActorDetails.objects.update_or_create(
    entity=actor_entity,
    defaults={"account": user, "display_name": "Custom example fallback"},
)
