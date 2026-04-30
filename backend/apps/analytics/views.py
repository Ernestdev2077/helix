from __future__ import annotations

from rest_framework import viewsets

from apps.workspaces.permissions import IsWorkspaceEditor

from .models import BanditArmState, MetricSnapshot
from .serializers import BanditArmStateSerializer, MetricSnapshotSerializer


class MetricSnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MetricSnapshotSerializer
    permission_classes = [IsWorkspaceEditor]
    lookup_field = "id"
    filterset_fields = ("publication",)

    def get_queryset(self):
        workspace = getattr(self.request, "workspace", None)
        if workspace is None:
            return MetricSnapshot.objects.none()
        return MetricSnapshot.objects.filter(workspace=workspace)


class BanditArmStateViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BanditArmStateSerializer
    permission_classes = [IsWorkspaceEditor]
    lookup_field = "id"
    filterset_fields = ("variant", "campaign")

    def get_queryset(self):
        workspace = getattr(self.request, "workspace", None)
        if workspace is None:
            return BanditArmState.objects.none()
        return BanditArmState.objects.filter(workspace=workspace)
