from __future__ import annotations

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.workspaces.permissions import IsWorkspaceEditor

from .models import AgentEvent, AgentRun
from .serializers import AgentEventSerializer, AgentRunSerializer


class AgentRunViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AgentRunSerializer
    permission_classes = [IsWorkspaceEditor]
    lookup_field = "id"
    filterset_fields = ("kind", "status", "post")

    def get_queryset(self):
        workspace = getattr(self.request, "workspace", None)
        if workspace is None:
            return AgentRun.objects.none()
        return AgentRun.objects.filter(workspace=workspace)

    @action(detail=True, methods=["get"])
    def events(self, request, id=None):  # noqa: A002,ARG002
        run = self.get_object()
        qs = AgentEvent.objects.filter(run=run).order_by("sequence")
        return Response(AgentEventSerializer(qs, many=True).data)
