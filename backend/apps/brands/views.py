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

    def perform_create(self, serializer: KBDocumentSerializer) -> None:
        from apps.brands.services import ingest_document

        doc = serializer.save()
        try:
            ingest_document(doc)
        except Exception:  # noqa: BLE001
            import logging

            logging.getLogger(__name__).warning(
                "KB ingest failed for doc %s", doc.id, exc_info=True
            )

    @action(detail=False, methods=["post"], url_path="paste")
    def paste(self, request):
        """Convenience for the onboarding wizard: create a doc from raw text and
        ingest it in one round-trip."""
        from apps.brands.models import KBDocument
        from apps.brands.services import ingest_document

        brand_id = request.data.get("brand")
        title = request.data.get("title", "").strip() or "Pasted note"
        raw_text = request.data.get("raw_text", "").strip()
        if not brand_id or not raw_text:
            return Response({"error": "brand and raw_text required"}, status=400)
        if not Brand.objects.filter(id=brand_id, workspace=request.workspace).exists():
            return Response({"error": "brand not found"}, status=404)

        doc = KBDocument.objects.create(
            brand_id=brand_id,
            title=title[:240],
            source_type=KBDocument.SourceType.PASTE,
            raw_text=raw_text,
        )
        try:
            chunk_count = ingest_document(doc)
        except Exception as exc:  # noqa: BLE001
            return Response({"error": "ingest_failed", "message": str(exc)}, status=502)
        return Response({
            **KBDocumentSerializer(doc).data,
            "chunk_count": chunk_count,
        })
