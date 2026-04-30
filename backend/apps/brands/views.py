from __future__ import annotations

from rest_framework import viewsets

from apps.workspaces.permissions import IsWorkspaceEditor

from .models import Brand, KBDocument
from .serializers import BrandSerializer, KBDocumentSerializer


class BrandViewSet(viewsets.ModelViewSet):
    serializer_class = BrandSerializer
    permission_classes = [IsWorkspaceEditor]
    lookup_field = "id"

    def get_queryset(self):
        workspace = getattr(self.request, "workspace", None)
        if workspace is None:
            return Brand.objects.none()
        return Brand.objects.filter(workspace=workspace)

    def perform_create(self, serializer: BrandSerializer) -> None:
        serializer.save(workspace=self.request.workspace)


class KBDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = KBDocumentSerializer
    permission_classes = [IsWorkspaceEditor]
    lookup_field = "id"

    def get_queryset(self):
        workspace = getattr(self.request, "workspace", None)
        if workspace is None:
            return KBDocument.objects.none()
        return KBDocument.objects.filter(brand__workspace=workspace)
