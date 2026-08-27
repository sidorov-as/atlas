"""Django admin for Team (Group) and Actor — routed through the core Entity
Service, not written directly.

Both kinds have no `CatalogEntity` common-metadata fields on their own model
(that lives on `CatalogEntity`, created together with the kind-specific
details row by `EntityService.create`) — so each admin form declares
`name`/`title`/`description` as plain extra fields and `save_model` builds
the `MetadataIn`/spec payloads `EntityService` expects, instead of using
Django's default `ModelForm.save()`.
"""

from contextlib import contextmanager

from atlas_plugin_api import (
    KIND_ACTOR,
    KIND_GROUP,
    MetadataIn,
    get_catalog_entity_model,
    get_entity_service,
    get_membership_service,
)
from django import forms
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from dmr.response import APIError

from .api.schemas import (
    ActorSpecIn,
    ActorSpecPatch,
    GroupSpecIn,
    GroupSpecPatch,
)
from .models import ActorDetails, GroupDetails


@contextmanager
def _translate_permission_errors():
    """`EntityWritePermission` raises `dmr.response.APIError` (an HTTP-response-
    shaped exception meant for REST controllers) — translated here to Django's
    own `PermissionDenied` so Django admin renders its normal 403 page instead
    of a 500 for a staff user without superuser rights (`is_group_member`
    requires one for the ownerless Group/Actor kinds — permissions.py)."""
    try:
        yield
    except APIError as exc:
        raise PermissionDenied(str(exc)) from exc


class GroupDetailsForm(forms.ModelForm):
    name = forms.CharField(max_length=255)
    title = forms.CharField(max_length=255, required=False)
    description = forms.CharField(widget=forms.Textarea, required=False)
    members = forms.ModelMultipleChoiceField(
        queryset=get_catalog_entity_model().objects.none(), required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["members"].queryset = get_catalog_entity_model().objects.filter(
            kind=KIND_ACTOR
        )

    class Meta:
        model = GroupDetails
        fields = ("type",)


@admin.register(GroupDetails)
class GroupDetailsAdmin(admin.ModelAdmin):
    form = GroupDetailsForm
    list_display = ("entity", "type")
    list_filter = ("type",)
    search_fields = ("entity__name", "entity__title")

    def get_form(self, request, obj=None, **kwargs):
        form_class = super().get_form(request, obj, **kwargs)
        if obj is not None:
            form_class.base_fields["name"].initial = obj.entity.name
            form_class.base_fields["title"].initial = obj.entity.title
            form_class.base_fields["description"].initial = obj.entity.description
            form_class.base_fields[
                "members"
            ].initial = get_membership_service().effective_members(obj)
        return form_class

    def save_model(self, request, obj, form, change):
        metadata = MetadataIn(
            name=form.cleaned_data["name"],
            title=form.cleaned_data["title"],
            description=form.cleaned_data["description"],
        )
        members = [member.ref for member in form.cleaned_data["members"]]
        with _translate_permission_errors():
            if change:
                spec = GroupSpecPatch(type=form.cleaned_data["type"], members=members)
                get_entity_service().update(
                    entity_id=obj.entity_id,
                    metadata=metadata,
                    spec=spec,
                    actor=request.user,
                )
            else:
                spec = GroupSpecIn(type=form.cleaned_data["type"], members=members)
                entity = get_entity_service().create(
                    kind_id=KIND_GROUP,
                    metadata=metadata,
                    spec=spec,
                    actor=request.user,
                )
                obj.entity = entity
                obj.pk = entity.pk


class ActorDetailsForm(forms.ModelForm):
    name = forms.CharField(max_length=255)
    title = forms.CharField(max_length=255, required=False)
    description = forms.CharField(widget=forms.Textarea, required=False)

    class Meta:
        model = ActorDetails
        fields = ("display_name", "email", "account")


@admin.register(ActorDetails)
class ActorDetailsAdmin(admin.ModelAdmin):
    form = ActorDetailsForm
    list_display = ("entity", "display_name", "email", "account")
    search_fields = ("entity__name", "display_name", "email")
    autocomplete_fields = ("account",)

    def get_form(self, request, obj=None, **kwargs):
        form_class = super().get_form(request, obj, **kwargs)
        if obj is not None:
            form_class.base_fields["name"].initial = obj.entity.name
            form_class.base_fields["title"].initial = obj.entity.title
            form_class.base_fields["description"].initial = obj.entity.description
        return form_class

    def save_model(self, request, obj, form, change):
        metadata = MetadataIn(
            name=form.cleaned_data["name"],
            title=form.cleaned_data["title"],
            description=form.cleaned_data["description"],
        )
        with _translate_permission_errors():
            if change:
                spec = ActorSpecPatch(
                    display_name=form.cleaned_data["display_name"],
                    email=form.cleaned_data["email"],
                )
                get_entity_service().update(
                    entity_id=obj.entity_id,
                    metadata=metadata,
                    spec=spec,
                    actor=request.user,
                )
                entity_id = obj.entity_id
            else:
                spec = ActorSpecIn(
                    display_name=form.cleaned_data["display_name"],
                    email=form.cleaned_data["email"],
                )
                entity = get_entity_service().create(
                    kind_id=KIND_ACTOR,
                    metadata=metadata,
                    spec=spec,
                    actor=request.user,
                )
                obj.entity = entity
                obj.pk = entity.pk
                entity_id = entity.pk
        # `account` (the Django auth login link) is admin-only plumbing, not
        # catalog domain data — it has no place in `ActorSpecIn`/`ActorSpecOut`
        # (schemas.py), so it's written directly rather than through the
        # Entity Service's `spec` pipeline.
        ActorDetails.objects.filter(pk=entity_id).update(
            account=form.cleaned_data["account"]
        )
