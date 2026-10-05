from django.contrib import admin

from .models import DatabaseSchema


@admin.register(DatabaseSchema)
class DatabaseSchemaAdmin(admin.ModelAdmin):
    list_display = ("entity", "dialect", "parse_status", "updated_at")
    list_filter = ("dialect", "parse_status")
    readonly_fields = ("created_at", "updated_at")
