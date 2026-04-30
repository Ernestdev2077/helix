from django.contrib import admin

from .models import Invite, Membership, Workspace


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "plan", "owner", "created_at")
    search_fields = ("name", "slug", "owner__email")
    list_filter = ("plan",)
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "workspace", "role", "created_at")
    list_filter = ("role",)
    search_fields = ("user__email", "workspace__name")


@admin.register(Invite)
class InviteAdmin(admin.ModelAdmin):
    list_display = ("email", "workspace", "role", "status", "expires_at")
    list_filter = ("status", "role")
    search_fields = ("email", "workspace__name")
    readonly_fields = ("token",)
