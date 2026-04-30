"""Workspace API endpoints.

- ``GET /api/v1/workspaces/`` — list workspaces current user belongs to
- ``POST /api/v1/workspaces/`` — create a new workspace (the creator becomes Owner)
- ``GET /api/v1/workspaces/<uuid>/`` — detail for a single workspace
- ``PATCH /api/v1/workspaces/<uuid>/`` — update name (Admin+)
- ``GET /api/v1/workspaces/<uuid>/members/`` — list members
- ``POST /api/v1/workspaces/<uuid>/invites/`` — invite by email (Admin+)
"""

from __future__ import annotations

from django.db import transaction
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Invite, Membership, Workspace
from .permissions import IsWorkspaceAdmin
from .serializers import InviteSerializer, MembershipSerializer, WorkspaceSerializer


class WorkspaceViewSet(viewsets.ModelViewSet):
    """CRUD for workspaces belonging to the current user."""

    serializer_class = WorkspaceSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Workspace.objects.none()
        return Workspace.objects.filter(memberships__user=user).distinct()

    @transaction.atomic
    def perform_create(self, serializer: WorkspaceSerializer) -> None:
        user = self.request.user
        workspace = serializer.save(owner=user)
        Membership.objects.create(
            workspace=workspace, user=user, role=Membership.Role.OWNER
        )

    @action(detail=True, methods=["get"])
    def members(self, request, id=None):  # noqa: A002
        workspace = self.get_object()
        qs = workspace.memberships.select_related("user").all()
        data = MembershipSerializer(qs, many=True).data
        return Response(data)


class InviteViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Create / list / revoke invites for the active workspace."""

    serializer_class = InviteSerializer
    permission_classes = [IsWorkspaceAdmin]
    lookup_field = "id"

    def get_queryset(self):
        workspace = getattr(self.request, "workspace", None)
        if workspace is None:
            return Invite.objects.none()
        return Invite.objects.filter(workspace=workspace)

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["workspace"] = getattr(self.request, "workspace", None)
        return ctx

    def destroy(self, request, *args, **kwargs):
        invite = self.get_object()
        invite.status = Invite.Status.REVOKED
        invite.save(update_fields=["status", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)
