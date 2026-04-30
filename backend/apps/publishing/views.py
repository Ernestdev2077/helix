from __future__ import annotations

from rest_framework import viewsets

from apps.workspaces.permissions import IsWorkspaceEditor

from .models import PlatformAccount, Publication
from .serializers import PlatformAccountSerializer, PublicationSerializer


class PlatformAccountViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only list of connected accounts. Creation happens via OAuth flow."""

    serializer_class = PlatformAccountSerializer
    permission_classes = [IsWorkspaceEditor]
    lookup_field = "id"

    def get_queryset(self):
        workspace = getattr(self.request, "workspace", None)
        if workspace is None:
            return PlatformAccount.objects.none()
        return PlatformAccount.objects.filter(workspace=workspace)


class PublicationViewSet(viewsets.ModelViewSet):
    serializer_class = PublicationSerializer
    permission_classes = [IsWorkspaceEditor]
    lookup_field = "id"

    def get_queryset(self):
        workspace = getattr(self.request, "workspace", None)
        if workspace is None:
            return Publication.objects.none()
        return Publication.objects.filter(workspace=workspace).select_related(
            "variant", "platform_account"
        )

    def perform_create(self, serializer) -> None:
        serializer.save(workspace=self.request.workspace)
