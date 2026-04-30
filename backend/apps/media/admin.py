from django.contrib import admin

from .models import MediaAsset


@admin.register(MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display = (
        "id", "source", "workspace", "brand", "mime_type",
        "width", "height", "size_bytes", "cost_usd", "created_at",
    )
    list_filter = ("source", "mime_type")
    search_fields = ("ai_prompt", "alt_text")
    readonly_fields = ("id", "created_at", "updated_at")
