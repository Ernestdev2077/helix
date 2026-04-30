from django.contrib import admin

from .models import Campaign, Post, PostVariant, PromptVersion, Reference, StyleRule, WinningPattern


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("name", "brand", "status", "starts_at", "created_at")
    list_filter = ("status",)
    search_fields = ("name", "brand__name")


class PostVariantInline(admin.TabularInline):
    model = PostVariant
    extra = 0
    readonly_fields = ("created_at",)
    fields = ("platform", "label", "status", "is_starred", "allocation_weight", "content")


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("id", "brand", "status", "target_platforms", "created_at")
    list_filter = ("status",)
    search_fields = ("brief",)
    inlines = [PostVariantInline]


@admin.register(PostVariant)
class PostVariantAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "platform", "label", "status", "is_starred")
    list_filter = ("platform", "status", "is_starred")


@admin.register(Reference)
class ReferenceAdmin(admin.ModelAdmin):
    list_display = ("id", "brand", "platform", "source", "likes_count", "use_count", "created_at")
    list_filter = ("platform", "source")
    search_fields = ("raw_text", "tags")


@admin.register(StyleRule)
class StyleRuleAdmin(admin.ModelAdmin):
    list_display = ("rule_text", "brand", "scope", "platform", "status", "confidence")
    list_filter = ("status", "scope", "platform")
    search_fields = ("rule_text", "brand__name")


@admin.register(WinningPattern)
class WinningPatternAdmin(admin.ModelAdmin):
    list_display = ("pattern_text", "brand", "platform", "lift", "sample_size", "created_at")
    list_filter = ("platform",)


@admin.register(PromptVersion)
class PromptVersionAdmin(admin.ModelAdmin):
    list_display = ("agent_name", "version", "workspace", "status", "eval_score", "created_at")
    list_filter = ("agent_name", "status")
