from __future__ import annotations

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

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

    @action(detail=True, methods=["post"])
    def curate(self, request, id=None):  # noqa: A002,ARG002
        """Trigger the Curator agent to propose StyleRules from likes + winners."""
        brand = self.get_object()
        from apps.agent_runs.services import start_curation

        run = start_curation(brand=brand, user=request.user)
        return Response({"agent_run_id": str(run.id), "brand_id": str(brand.id)})


class KBDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = KBDocumentSerializer
    permission_classes = [IsWorkspaceEditor]
    lookup_field = "id"

    def get_queryset(self):
        workspace = getattr(self.request, "workspace", None)
        if workspace is None:
            return KBDocument.objects.none()
        return KBDocument.objects.filter(brand__workspace=workspace)
