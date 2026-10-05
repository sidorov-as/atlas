from django import forms
from django.contrib import admin

from .models import ConflictRecord, IngestionIssue, RegisteredRepository


class RegisteredRepositoryAdminForm(forms.ModelForm):
    """Validates `source_id` against the currently resolved `atlas.ingestion`
    `sources` config at save time (`source_id` is validated
    against the currently resolved sources config in the admin form
    via clean()/full_clean(); an unknown source is
    rejected).

    Free-text `source_id` plus this `clean()` check, not a dynamically
    populated `ChoiceField`: a
    `ChoiceField` would need the admin form to read resolved plugin config
    at form-render time, a pattern not otherwise used in this codebase.
    `clean()`-time validation gets the same fail-fast guarantee — a typo
    surfaces immediately, per that Risk — with no new plumbing, at the cost
    of no dropdown UX; a reasonable fast-follow if that UX is later worth
    the plumbing.
    """

    class Meta:
        model = RegisteredRepository
        fields = "__all__"

    def clean_source_id(self) -> str:
        from atlas_plugin_api import get_plugin_config

        from .config import IngestionPluginConfig
        from .plugin import PLUGIN

        source_id = self.cleaned_data["source_id"]
        try:
            config = get_plugin_config(PLUGIN.id, IngestionPluginConfig)
        except LookupError:
            config = IngestionPluginConfig()
        known_source_ids = {source.id for source in config.sources}
        if source_id not in known_source_ids:
            raise forms.ValidationError(
                f"{source_id!r} does not match any source currently "
                "configured for atlas.ingestion.",
            )
        return source_id


@admin.register(RegisteredRepository)
class RegisteredRepositoryAdmin(admin.ModelAdmin):
    """`on_delete=PROTECT` on `EntityClaim.repository` is what
    actually blocks deletion while a repository still claims an entity — Django
    admin's delete flow surfaces that as a "cannot delete" page listing every
    claiming entity.

    This block is status-blind by construction (a plain FK doesn't know about
    `status`), so it already covers the modified requirement correctly: an
    entity claimed via `source_kind=yaml` still blocks unregistration whether
    it's `active` or `removed` — cascade-delete and orphan-and-keep are not
    supported. The way to actually clear a claimed entity is Remove (if still
    active) followed by Purge with a valid Purge Grant
    there is no other supported path,
    since manual writes against a `source_kind=yaml` entity are unconditionally
    rejected (ADR 0001)."""

    form = RegisteredRepositoryAdminForm
    list_display = ("source_id", "path", "default_branch", "created_at")
    search_fields = ("source_id", "path")


@admin.register(ConflictRecord)
class ConflictRecordAdmin(admin.ModelAdmin):
    list_display = (
        "kind",
        "namespace",
        "name",
        "repo_full_name",
        "reason",
        "is_active",
        "first_seen",
        "last_seen",
    )
    list_filter = ("is_active", "reason", "kind")
    search_fields = ("name", "repo_full_name")
    readonly_fields = ("first_seen", "last_seen")


@admin.register(IngestionIssue)
class IngestionIssueAdmin(admin.ModelAdmin):
    list_display = (
        "repo_full_name",
        "path",
        "message",
        "is_active",
        "first_seen",
        "last_seen",
    )
    list_filter = ("is_active",)
    search_fields = ("path", "message")
    readonly_fields = ("first_seen", "last_seen")
