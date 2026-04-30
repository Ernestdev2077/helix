from django.contrib import admin

from .models import Brand, KBChunk, KBDocument


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "workspace", "created_at")
    search_fields = ("name", "slug", "workspace__name")


@admin.register(KBDocument)
class KBDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "brand", "source_type", "status", "token_count", "created_at")
    list_filter = ("status", "source_type")
    search_fields = ("title", "brand__name")


@admin.register(KBChunk)
class KBChunkAdmin(admin.ModelAdmin):
    list_display = ("document", "position", "token_count")
    search_fields = ("document__title",)
