from typing import ClassVar

from django.contrib import admin, messages

from .models import (
    ApiDetails,
    ApiEndpoint,
    ApiOperation,
    ServiceEndpointUsage,
    ServiceOperationUsage,
)


@admin.register(ApiDetails)
class ApiDetailsAdmin(admin.ModelAdmin):
    """Surfaces spec-resolution and endpoint/operation-sync status for
    operators — `spec_resolved_at`/`spec_resolve_failed`,
    `endpoints_synced_at`/`endpoints_sync_failed`
    and
    `operations_synced_at`/`operations_sync_failed`
    are all system-written, so
    every one of them is read-only here.
    """

    list_display = (
        "entity",
        "type",
        "spec_source",
        "spec_resolved_at",
        "spec_resolve_failed",
        "endpoints_synced_at",
        "endpoints_sync_failed",
        "operations_synced_at",
        "operations_sync_failed",
    )
    list_filter = (
        "type",
        "spec_source",
        "spec_resolve_failed",
        "endpoints_sync_failed",
        "operations_sync_failed",
    )
    search_fields = ("entity__name",)
    autocomplete_fields = ("entity", "system")
    readonly_fields = (
        "spec_resolved_at",
        "spec_resolve_failed",
        "endpoints_synced_at",
        "endpoints_sync_failed",
        "operations_synced_at",
        "operations_sync_failed",
    )


@admin.register(ApiEndpoint)
class ApiEndpointAdmin(admin.ModelAdmin):
    """Django admin is the only authoring surface for `Endpoint` documentation
    (no self-service create/edit API).

    Removal is soft (`status=removed`, `mark_as_removed`) so existing
    `ServiceEndpointUsage` links stay intact; the default hard-delete action
    is disabled so removal can only happen that way.
    """

    list_display = ("method", "path", "api", "status", "deprecated", "updated_at")
    list_filter = ("method", "status", "deprecated")
    search_fields = ("path", "operation_id", "summary", "api__name")
    autocomplete_fields = ("api",)
    actions: ClassVar[list] = ["mark_as_removed"]

    @admin.action(description="Mark selected endpoints as removed")
    def mark_as_removed(self, request, queryset):
        updated = queryset.exclude(status=ApiEndpoint.STATUS_REMOVED).update(
            status=ApiEndpoint.STATUS_REMOVED
        )
        self.message_user(
            request, f"{updated} endpoint(s) marked as removed.", messages.SUCCESS
        )

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ServiceEndpointUsage)
class ServiceEndpointUsageAdmin(admin.ModelAdmin):
    list_display = (
        "endpoint",
        "service",
        "origin",
        "source",
        "created_by",
        "created_at",
    )
    list_filter = ("origin", "source")
    search_fields = ("endpoint__path", "service__name")
    autocomplete_fields = ("endpoint", "service", "created_by")
    readonly_fields = ("origin", "source", "created_at")


@admin.register(ApiOperation)
class ApiOperationAdmin(admin.ModelAdmin):
    """Django admin is the only authoring surface for `Operation`
    documentation (no self-service create/edit API).

    Removal is soft (`status=removed`, `mark_as_removed`) so existing
    `ServiceOperationUsage` links stay intact; the default hard-delete
    action is disabled so removal can only happen that way. Marking as
    removed through this action is recorded in the standard admin change
    log (Django admin's own `log_change`/`LogEntry` behavior for an action
    that saves a model change) — no bespoke audit trail needed.
    """

    list_display = (
        "channel_address",
        "direction",
        "api",
        "status",
        "deprecated",
        "updated_at",
    )
    list_filter = ("direction", "status", "deprecated")
    search_fields = (
        "channel_address",
        "operation_key",
        "operation_id",
        "summary",
        "api__name",
    )
    autocomplete_fields = ("api",)
    actions: ClassVar[list] = ["mark_as_removed"]

    @admin.action(description="Mark selected operations as removed")
    def mark_as_removed(self, request, queryset):
        updated = 0
        for operation in queryset.exclude(status=ApiOperation.STATUS_REMOVED):
            operation.status = ApiOperation.STATUS_REMOVED
            operation.save(update_fields=["status", "updated_at"])
            self.log_change(request, operation, "Marked as removed")
            updated += 1
        self.message_user(
            request, f"{updated} operation(s) marked as removed.", messages.SUCCESS
        )

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ServiceOperationUsage)
class ServiceOperationUsageAdmin(admin.ModelAdmin):
    list_display = (
        "operation",
        "service",
        "role",
        "origin",
        "source",
        "created_by",
        "created_at",
    )
    list_filter = ("role", "origin", "source")
    search_fields = ("operation__channel_address", "service__name")
    autocomplete_fields = ("operation", "service", "created_by")
    readonly_fields = ("origin", "source", "created_at")
