from __future__ import annotations

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.workspaces.permissions import IsWorkspaceEditor

from .models import Campaign, Post, PostVariant, Reference, StyleRule, WinningPattern
from .serializers import (
    CampaignSerializer,
    PostSerializer,
    PostVariantSerializer,
    ReferenceSerializer,
    StyleRuleSerializer,
    WinningPatternSerializer,
)


class _WorkspaceScopedViewSet(viewsets.ModelViewSet):
    """Base viewset that scopes queryset to the active workspace and sets it on create."""

    permission_classes = [IsWorkspaceEditor]
    lookup_field = "id"
    workspace_field = "workspace"

    def get_queryset(self):
        workspace = getattr(self.request, "workspace", None)
        if workspace is None:
            return self.queryset.none()
        return self.queryset.filter(**{self.workspace_field: workspace})

    def perform_create(self, serializer) -> None:
        serializer.save(
            workspace=self.request.workspace,
            created_by=self.request.user if hasattr(serializer.Meta.model, "created_by") else None,
        )


class CampaignViewSet(_WorkspaceScopedViewSet):
    queryset = Campaign.objects.all()
    serializer_class = CampaignSerializer

    def perform_create(self, serializer) -> None:
        serializer.save(
            workspace=self.request.workspace,
            created_by=self.request.user,
        )


class PostViewSet(_WorkspaceScopedViewSet):
    queryset = Post.objects.prefetch_related("variants").all()
    serializer_class = PostSerializer

    def perform_create(self, serializer) -> None:
        serializer.save(
            workspace=self.request.workspace,
            created_by=self.request.user,
        )

    @action(detail=True, methods=["post"])
    def generate(self, request, id=None):  # noqa: A002
        """Kick off a LangGraph run to generate variants for this post.

        Returns an ``agent_run_id`` that the client subscribes to via WebSocket.
        """
        post = self.get_object()
        from apps.agent_runs.services import start_content_generation

        run = start_content_generation(
            post=post,
            user=request.user,
        )
        return Response({"agent_run_id": str(run.id), "post_id": str(post.id)})


class PostVariantViewSet(viewsets.ModelViewSet):
    queryset = PostVariant.objects.all()
    serializer_class = PostVariantSerializer
    permission_classes = [IsWorkspaceEditor]
    lookup_field = "id"

    def get_queryset(self):
        workspace = getattr(self.request, "workspace", None)
        if workspace is None:
            return PostVariant.objects.none()
        return PostVariant.objects.filter(post__workspace=workspace)


class ReferenceViewSet(_WorkspaceScopedViewSet):
    queryset = Reference.objects.all()
    serializer_class = ReferenceSerializer

    def perform_create(self, serializer) -> None:
        serializer.save(
            workspace=self.request.workspace,
            added_by=self.request.user,
        )


class StyleRuleViewSet(_WorkspaceScopedViewSet):
    queryset = StyleRule.objects.all()
    serializer_class = StyleRuleSerializer

    @action(detail=True, methods=["post"])
    def approve(self, request, id=None):  # noqa: A002
        from django.utils import timezone

        rule = self.get_object()
        rule.status = StyleRule.Status.APPROVED
        rule.reviewed_by = request.user
        rule.reviewed_at = timezone.now()
        rule.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
        return Response(StyleRuleSerializer(rule).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, id=None):  # noqa: A002
        from django.utils import timezone

        rule = self.get_object()
        rule.status = StyleRule.Status.REJECTED
        rule.reviewed_by = request.user
        rule.reviewed_at = timezone.now()
        rule.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
        return Response(StyleRuleSerializer(rule).data)


class WinningPatternViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WinningPattern.objects.all()
    serializer_class = WinningPatternSerializer
    permission_classes = [IsWorkspaceEditor]
    lookup_field = "id"

    def get_queryset(self):
        workspace = getattr(self.request, "workspace", None)
        if workspace is None:
            return WinningPattern.objects.none()
        return WinningPattern.objects.filter(workspace=workspace)
