from django.contrib import admin

from .models import Flow


@admin.register(Flow)
class FlowAdmin(admin.ModelAdmin):
    list_display = ("name", "system")
    list_filter = ("system",)
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at")
