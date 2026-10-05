from datetime import timedelta

from django import forms
from django.contrib import admin
from django.contrib.admin import helpers
from django.contrib.admin.options import ActionLocation, BaseModelAdmin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache

from .authorization import is_account_read_only
from .models import (
    AccountAccess,
    AccountAccessAuditRecord,
    ArchitectureRelationship,
    AuthenticationSecurityEvent,
    AuthenticationSourceBinding,
    CatalogEntity,
    ExternalIdentityLink,
    GroupMembershipGrant,
    MembershipGrantAuditRecord,
    PersonalAccessToken,
    ProvisioningAuditRecord,
    PurgeGrant,
)
from .services.pat_service import issue_personal_access_token

User = get_user_model()


# A mandatory Core restriction on Django admin
# itself, applied once here rather than mixed into every `ModelAdmin`
# subclass across Core and every plugin (`apis`, `flows`, `ingestion`,
# `standard-catalog`) — the same "one shared guard, not a per-site
# reimplementation" shape as `CoreGuardedEvaluator`
# and `is_account_read_only` itself. `has_add/change/delete_permission` are
# defined once on `BaseModelAdmin`, the shared parent of both `ModelAdmin`
# and `InlineModelAdmin` (`InlineModelAdmin`'s own overrides delegate to
# `super()` for the non-`auto_created` case, which is every inline in this
# codebase), so wrapping them there covers every registered model, inline,
# and any plugin's admin classes without editing plugin code or trusting
# each plugin author to remember the restriction. `has_view_permission` is
# untouched, so authorized viewing is preserved exactly as before — Django
# renders the change form read-only when view is allowed but change is not,
# which is also what stops a read-only administrator from clearing its own
# `AccountAccess` restriction through a crafted `UserAdmin` POST without
# `AccountAccessInline` needing its own copy of this check.
#
# `get_actions` (bulk actions, including the default `delete_selected` and
# plugin-declared custom actions like `apis`' `mark_as_removed`) is guarded
# separately: only `ModelAdmin` has it (inlines have no action list), and
# Django only gates a custom action by permission when the action itself
# declares `allowed_permissions` — an action that doesn't (as none here do)
# runs regardless of `has_*_permission`. Blanking the action list for a
# read-only operator closes that gap without requiring every current and
# future action to opt in individually.
_unguarded_has_add_permission = BaseModelAdmin.has_add_permission
_unguarded_has_change_permission = BaseModelAdmin.has_change_permission
_unguarded_has_delete_permission = BaseModelAdmin.has_delete_permission
_unguarded_get_actions = admin.ModelAdmin.get_actions


def _read_only_guarded_has_add_permission(self, request, *args, **kwargs):
    if is_account_read_only(request.user):
        return False
    return _unguarded_has_add_permission(self, request, *args, **kwargs)


def _read_only_guarded_has_change_permission(self, request, obj=None):
    if is_account_read_only(request.user):
        return False
    return _unguarded_has_change_permission(self, request, obj)


def _read_only_guarded_has_delete_permission(self, request, obj=None):
    if is_account_read_only(request.user):
        return False
    return _unguarded_has_delete_permission(self, request, obj)


def _read_only_guarded_get_actions(
    self,
    request,
    action_location=ActionLocation.CHANGE_LIST,
):
    if is_account_read_only(request.user):
        return {}
    return _unguarded_get_actions(
        self, request, action_location=action_location
    )


BaseModelAdmin.has_add_permission = (  # type: ignore[method-assign]
    _read_only_guarded_has_add_permission
)
BaseModelAdmin.has_change_permission = (  # type: ignore[method-assign]
    _read_only_guarded_has_change_permission
)
BaseModelAdmin.has_delete_permission = (  # type: ignore[method-assign]
    _read_only_guarded_has_delete_permission
)
admin.ModelAdmin.get_actions = (  # type: ignore[method-assign]
    _read_only_guarded_get_actions
)


@admin.register(CatalogEntity)
class CatalogEntityAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "namespace", "owner", "source_kind")
    list_filter = ("kind", "source_kind")
    search_fields = ("name", "title")
    autocomplete_fields = ("owner",)


@admin.register(ArchitectureRelationship)
class ArchitectureRelationshipAdmin(admin.ModelAdmin):
    list_display = (
        "source",
        "target",
        "label",
        "interaction_kind",
        "origin",
    )
    list_filter = ("interaction_kind", "origin")
    search_fields = ("label", "technology")
    autocomplete_fields = ("source", "target")


@admin.register(ExternalIdentityLink)
class ExternalIdentityLinkAdmin(admin.ModelAdmin):
    list_display = (
        "provider_id",
        "source_id",
        "external_subject",
        "user",
        "created_at",
    )
    list_filter = ("provider_id",)
    search_fields = ("external_subject", "user__username")
    autocomplete_fields = ("user",)


@admin.register(AuthenticationSourceBinding)
class AuthenticationSourceBindingAdmin(admin.ModelAdmin):
    list_display = (
        "provider_id",
        "source_id",
        "generation",
        "activated_at",
        "revoked_at",
    )
    readonly_fields = (
        "provider_id",
        "source_id",
        "configuration_fingerprint",
        "lock_digest",
        "generation",
        "activated_at",
        "revoked_at",
    )


class _AppendOnlyAuthenticationEventAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ProvisioningAuditRecord)
class ProvisioningAuditRecordAdmin(_AppendOnlyAuthenticationEventAdmin):
    list_display = (
        "timestamp",
        "action",
        "provider_id",
        "principal_id",
        "correlation_id",
    )
    list_filter = ("action", "provider_id")


@admin.register(AuthenticationSecurityEvent)
class AuthenticationSecurityEventAdmin(_AppendOnlyAuthenticationEventAdmin):
    list_display = (
        "timestamp",
        "category",
        "provider_id",
        "stage",
        "correlation_id",
    )
    list_filter = ("category", "provider_id", "stage")


@admin.register(GroupMembershipGrant)
class GroupMembershipGrantAdmin(admin.ModelAdmin):
    list_display = (
        "group",
        "actor",
        "source_kind",
        "identity_link",
        "legacy_unclassified",
        "expires_at",
        "revoked_at",
    )
    list_filter = ("source_kind", "legacy_unclassified")
    autocomplete_fields = ("group", "actor", "identity_link")
    readonly_fields = (
        "group",
        "actor",
        "source_kind",
        "identity_link",
        "external_key",
        "legacy_unclassified",
        "expires_at",
        "revoked_at",
        "created_at",
        "last_confirmed_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(MembershipGrantAuditRecord)
class MembershipGrantAuditRecordAdmin(admin.ModelAdmin):
    list_display = ("grant_id", "group_id", "actor_id", "action", "timestamp")
    readonly_fields = (
        "grant_id",
        "group_id",
        "actor_id",
        "identity_link_id",
        "action",
        "operator",
        "reason",
        "timestamp",
        "details",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PurgeGrant)
class PurgeGrantAdmin(admin.ModelAdmin):
    list_display = ("group", "grantee", "granted_by", "created_at")
    autocomplete_fields = ("group", "grantee", "granted_by")


class IssuePersonalAccessTokenForm(forms.Form):
    owner = forms.ModelChoiceField(queryset=User.objects.filter(is_active=True))
    name = forms.CharField(
        max_length=255,
        required=False,
        help_text="Optional label, e.g. the client the token is for.",
    )
    scopes = forms.MultipleChoiceField(
        choices=PersonalAccessToken.SCOPE_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text=(
            "Scopes narrow, never broaden, the owner's own permissions. "
            "A token with no scopes can authenticate but cannot write."
        ),
    )
    expires_in_days = forms.IntegerField(
        min_value=1,
        required=False,
        help_text="Leave empty for a token that never expires.",
    )


@admin.register(PersonalAccessToken)
class PersonalAccessTokenAdmin(admin.ModelAdmin):
    """Browsing, issuance, and revocation for Personal Access Tokens.

    "Add" is replaced by `issue_view`: a token is minted through
    `issue_personal_access_token()` (the same path as `manage.py issue_pat`)
    and its plaintext is rendered once, directly in that POST response —
    never redirected to or stored, since Atlas keeps only a hash. Django
    admin's own add form would instead write the model fields directly, so
    `prefix`/`token_hash` stay read-only, identification only. Revocation is
    the `revoke_tokens` bulk action (sets `revoked_at`, keeping the row for
    audit).
    """

    list_display = (
        "owner",
        "name",
        "prefix",
        "scopes",
        "expires_at",
        "revoked_at",
        "last_used_at",
        "created_at",
    )
    list_filter = ("revoked_at",)
    search_fields = ("owner__username", "name", "prefix")
    autocomplete_fields = ("owner",)
    readonly_fields = ("prefix", "token_hash", "last_used_at", "created_at")
    actions = ("revoke_tokens",)

    def get_urls(self):
        return [
            path(
                "issue/",
                self.admin_site.admin_view(self.issue_view),
                name="catalog_personalaccesstoken_issue",
            ),
            *super().get_urls(),
        ]

    def add_view(self, request, form_url="", extra_context=None):
        return redirect("admin:catalog_personalaccesstoken_issue")

    @method_decorator(never_cache)
    def issue_view(self, request):
        if not self.has_add_permission(request):
            raise PermissionDenied
        form = IssuePersonalAccessTokenForm(
            request.POST or None, initial={"owner": request.user.pk}
        )
        issued = None
        if request.method == "POST" and form.is_valid():
            days = form.cleaned_data["expires_in_days"]
            issued = issue_personal_access_token(
                owner=form.cleaned_data["owner"],
                name=form.cleaned_data["name"],
                scopes=form.cleaned_data["scopes"],
                expires_at=timezone.now() + timedelta(days=days)
                if days
                else None,
            )
        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "Issue personal access token",
            "adminform": helpers.AdminForm(
                form,
                [(None, {"fields": list(form.fields)})],
                {},
                model_admin=self,
            ),
            "media": self.media + form.media,
            "issued": issued,
        }
        return TemplateResponse(
            request, "admin/catalog/personalaccesstoken/issue.html", context
        )

    @admin.action(description="Revoke selected tokens", permissions=["change"])
    def revoke_tokens(self, request, queryset):
        revoked = queryset.filter(revoked_at__isnull=True).update(
            revoked_at=timezone.now()
        )
        self.message_user(request, f"Revoked {revoked} token(s).")


class AccountAccessInline(admin.StackedInline):
    """Exposes `AccountAccess.read_only` on the User change form
    `can_delete = False`: the
    normal UI sets `read_only=False` explicitly rather than deleting the
    row, since deleting it would silently restore the default-unrestricted
    state as an unaudited bypass. `extra`/`max_num` render exactly one
    form — blank for a user with no row yet, bound for one that has it —
    matching the "OneToOne side-car" admin pattern.

    Beyond Django's own `catalog.add_accountaccess`/`change_accountaccess`
    permission (checked by the base class), the module-level guard above
    stops the operator submitting this inline from themselves being flagged
    read-only — this is what stops a read-only administrator from clearing
    its own restriction via a crafted UserAdmin POST. Django's inline
    formset already ignores edits to existing rows when
    `has_change_permission` is False (`InlineModelAdmin.get_formset`'s
    `DeleteProtectedModelForm.has_changed`), so this isn't just a UI hint.
    """

    model = AccountAccess
    can_delete = False
    fields = ("read_only",)
    extra = 1
    max_num = 1
    verbose_name_plural = "Account access"


# `server.apps.catalog` is imported by admin autodiscovery before
# `django.contrib.auth` (its `django_apps` precede `additional_apps` in
# `resolve_installed_apps`), so `User` isn't registered yet when this
# module runs. Unregistering defensively — rather than relying on that
# ordering — means this doesn't silently stop working if that ordering
# ever changes; `django.contrib.auth.admin`'s own registration already
# no-ops via the same `AlreadyRegistered` catch if it runs after us.
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:  # type: ignore[attr-defined]
    pass


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """Replaces Django's stock `UserAdmin` registration solely to attach
    `AccountAccessInline` (no other customization) — there is no existing
    custom `UserAdmin` here to extend, and `AUTH_USER_MODEL` stays the
    stock `django.contrib.auth.models.User`.
    """

    inlines = (*DjangoUserAdmin.inlines, AccountAccessInline)

    def save_formset(self, request, form, formset, change):
        if formset.model is not AccountAccess:
            super().save_formset(request, form, formset, change)
            return

        # `_changeform_view` already wraps this whole POST handler in
        # `transaction.atomic()` (Django's `ModelAdmin.changeform_view`),
        # so the User row `save_model` just committed, this AccountAccess
        # write, and its audit record below land in one transaction
        # (the change and its audit event commit atomically
        # together). `can_delete = False` on the inline means
        # `formset.deleted_objects` is always empty here.
        for instance in formset.save(commit=False):
            is_new = instance._state.adding
            old_read_only = None
            if not is_new:
                old_read_only = (
                    AccountAccess.objects.filter(
                        pk=instance.pk,
                    )
                    .values_list("read_only", flat=True)
                    .first()
                )
            instance.save()
            AccountAccessAuditRecord.objects.create(
                target_id=instance.account_id,
                target_username=instance.account.get_username(),
                operator=request.user,
                action=(
                    AccountAccessAuditRecord.ACTION_CREATE
                    if is_new
                    else AccountAccessAuditRecord.ACTION_UPDATE
                ),
                old_read_only=old_read_only,
                new_read_only=instance.read_only,
            )
        formset.save_m2m()
