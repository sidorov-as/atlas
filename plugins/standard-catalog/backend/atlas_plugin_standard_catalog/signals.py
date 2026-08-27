"""Wires Standard Catalog entity writes to `recompute_relations`.

Split out of `server.apps.catalog.signals`
— connected here, for System/Component/Resource/Group/Actor's `*Details`
models, since those models now live in this plugin; `recompute_relations`
itself stays core (kind-agnostic, keyed only by `CatalogEntity.kind` string
constants). `ApiDetails`' signal wiring stays in
`server.apps.catalog.signals`, since `ApiDetails` hasn't moved.
"""

from atlas_plugin_api import get_membership_grant_model, recompute_relations
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from .models import (
    ActorDetails,
    ComponentDetails,
    GroupDetails,
    ResourceDetails,
    SystemDetails,
)

_M2M_WRITE_ACTIONS = {"post_add", "post_remove", "post_clear"}


@receiver(post_save, sender=SystemDetails)
@receiver(post_save, sender=ComponentDetails)
@receiver(post_save, sender=ResourceDetails)
@receiver(post_save, sender=GroupDetails)
@receiver(post_save, sender=ActorDetails)
def _recompute_on_save(sender, instance, **kwargs):
    recompute_relations(instance.entity)


def _recompute_on_m2m_change(
    sender, instance, action, reverse, model, pk_set, **kwargs
):
    if action not in _M2M_WRITE_ACTIONS:
        return
    if not reverse:
        recompute_relations(instance.entity)
        return
    if not pk_set:
        return
    for details in model.objects.filter(pk__in=pk_set).select_related("entity"):
        recompute_relations(details.entity)


for _m2m_field in (
    ComponentDetails.depends_on,
    ComponentDetails.provides_apis,
    ComponentDetails.consumes_apis,
    GroupDetails.members,
):
    m2m_changed.connect(_recompute_on_m2m_change, sender=_m2m_field.through)


def _recompute_on_membership_grant_change(sender, instance, **kwargs):
    recompute_relations(instance.group.entity)
    recompute_relations(instance.actor)


GroupMembershipGrant = get_membership_grant_model()
post_save.connect(_recompute_on_membership_grant_change, sender=GroupMembershipGrant)
post_delete.connect(_recompute_on_membership_grant_change, sender=GroupMembershipGrant)
