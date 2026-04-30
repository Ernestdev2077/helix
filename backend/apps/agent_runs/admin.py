from django.contrib import admin

from .models import AgentEvent, AgentRun


class AgentEventInline(admin.TabularInline):
    model = AgentEvent
    extra = 0
    readonly_fields = ("sequence", "kind", "node_name", "message", "data", "created_at")
    fields = readonly_fields


@admin.register(AgentRun)
class AgentRunAdmin(admin.ModelAdmin):
    list_display = ("id", "kind", "status", "workspace", "post", "created_at")
    list_filter = ("kind", "status")
    search_fields = ("id", "post__id")
    inlines = [AgentEventInline]


@admin.register(AgentEvent)
class AgentEventAdmin(admin.ModelAdmin):
    list_display = ("run", "sequence", "kind", "node_name", "created_at")
    list_filter = ("kind",)
