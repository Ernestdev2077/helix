"""DRF permissions for workspace-scoped endpoints."""

from __future__ import annotations

from rest_framework import permissions

from .models import Membership


class HasActiveWorkspace(permissions.BasePermission):
    """Ensures the request has a resolved workspace and membership."""

    message = "No active workspace for this request."

    def has_permission(self, request, view) -> bool:  # noqa: ARG002
        return (
            getattr(request, "user", None) is not None
            and request.user.is_authenticated
            and getattr(request, "workspace", None) is not None
            and getattr(request, "membership", None) is not None
        )


class IsWorkspaceEditor(HasActiveWorkspace):
    """Editor+ can mutate, everyone in the workspace can read."""

    editor_roles = {
        Membership.Role.OWNER,
        Membership.Role.ADMIN,
        Membership.Role.EDITOR,
    }

    def has_permission(self, request, view) -> bool:
        if not super().has_permission(request, view):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.membership.role in self.editor_roles


class IsWorkspaceAdmin(HasActiveWorkspace):
    """Admin/Owner only — used for billing, member management, destructive ops."""

    admin_roles = {Membership.Role.OWNER, Membership.Role.ADMIN}

    def has_permission(self, request, view) -> bool:
        if not super().has_permission(request, view):
            return False
        return request.membership.role in self.admin_roles
