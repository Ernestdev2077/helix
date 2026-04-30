from django.contrib import admin

from .models import PlatformAccount, Publication


@admin.register(PlatformAccount)
class PlatformAccountAdmin(admin.ModelAdmin):
    list_display = ("platform", "handle", "workspace", "status", "created_at")
    list_filter = ("platform", "status")
    search_fields = ("handle", "workspace__name")
    readonly_fields = ("access_token", "refresh_token")


@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display = ("id", "variant", "platform_account", "status", "scheduled_for", "published_at")
    list_filter = ("status",)
    search_fields = ("external_id", "external_url")
