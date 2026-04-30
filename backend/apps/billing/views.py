from __future__ import annotations

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.workspaces.permissions import HasActiveWorkspace, IsWorkspaceAdmin

from .models import CreditLedger, Subscription
from .serializers import CreditLedgerSerializer, SubscriptionSerializer


class SubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SubscriptionSerializer
    permission_classes = [HasActiveWorkspace]
    lookup_field = "id"

    def get_queryset(self):
        workspace = getattr(self.request, "workspace", None)
        if workspace is None:
            return Subscription.objects.none()
        return Subscription.objects.filter(workspace=workspace)

    @action(detail=False, methods=["get"], permission_classes=[HasActiveWorkspace])
    def current(self, request):
        sub = Subscription.objects.filter(workspace=request.workspace).first()
        if sub is None:
            return Response({"status": "none"})
        return Response(SubscriptionSerializer(sub).data)


class CreditLedgerViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CreditLedgerSerializer
    permission_classes = [IsWorkspaceAdmin]
    lookup_field = "id"

    def get_queryset(self):
        workspace = getattr(self.request, "workspace", None)
        if workspace is None:
            return CreditLedger.objects.none()
        return CreditLedger.objects.filter(workspace=workspace)
