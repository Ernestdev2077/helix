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

    @action(detail=True, methods=["post"])
    def star(self, request, id=None):  # noqa: A002,ARG002
        """Mark variant as the A/B winner and auto-create a Reference for the learning loop."""
        variant = self.get_object()
        post = variant.post

        PostVariant.objects.filter(post=post, platform=variant.platform).update(is_starred=False)
        variant.is_starred = True
        variant.save(update_fields=["is_starred", "updated_at"])

        Reference.objects.update_or_create(
            workspace=post.workspace,
            brand=post.brand,
            platform=variant.platform,
            raw_text=variant.content,
            defaults={
                "source": Reference.Source.WINNER,
                "source_url": "",
                "tags": ["winner", post.brand.slug or "brand"],
                "added_by": request.user,
            },
        )
        return Response(PostVariantSerializer(variant).data)

    @action(detail=True, methods=["post"])
    def unstar(self, request, id=None):  # noqa: A002,ARG002
        variant = self.get_object()
        variant.is_starred = False
        variant.save(update_fields=["is_starred", "updated_at"])
        return Response(PostVariantSerializer(variant).data)

    @action(detail=True, methods=["post"])
    def refine(self, request, id=None):  # noqa: A002,ARG002
        """A/B refine — generate N reframings with different psych triggers.

        Returns an agent_run_id; the SPA subscribes via WebSocket and the new
        variants are appended to the same post (labels continue past the max).
        """
        variant = self.get_object()
        from apps.agent_runs.services import start_ab_variation

        run = start_ab_variation(variant=variant, user=request.user)
        return Response({
            "agent_run_id": str(run.id),
            "post_id": str(variant.post_id),
            "source_variant_id": str(variant.id),
        })

    @action(detail=True, methods=["post"], url_path="attach-image")
    def attach_image(self, request, id=None):  # noqa: A002,ARG002
        """Attach an existing MediaAsset (uploaded earlier) to this variant."""
        from apps.media.models import MediaAsset
        from apps.media.serializers import MediaAssetSerializer

        variant = self.get_object()
        asset_id = request.data.get("asset_id")
        if not asset_id:
            return Response({"error": "asset_id required"}, status=400)
        try:
            asset = MediaAsset.objects.get(id=asset_id, workspace=variant.post.workspace)
        except MediaAsset.DoesNotExist:
            return Response({"error": "asset not found"}, status=404)

        asset_url = (
            request.build_absolute_uri(asset.url)
            if asset.file and not asset.url.startswith(("http://", "https://"))
            else asset.url
        )
        media_entry = {
            "asset_id": str(asset.id),
            "type": "image",
            "url": asset_url,
            "alt": asset.alt_text,
            "width": asset.width,
            "height": asset.height,
            "source": asset.source,
        }
        variant.media = [media_entry]
        variant.save(update_fields=["media", "updated_at"])
        return Response({
            "variant": PostVariantSerializer(variant).data,
            "asset": MediaAssetSerializer(asset, context={"request": request}).data,
        })

    @action(detail=True, methods=["post"], url_path="detach-image")
    def detach_image(self, request, id=None):  # noqa: A002,ARG002
        variant = self.get_object()
        variant.media = []
        variant.save(update_fields=["media", "updated_at"])
        return Response(PostVariantSerializer(variant).data)

    @action(detail=True, methods=["post"], url_path="generate-image")
    def generate_image(self, request, id=None):  # noqa: A002,ARG002
        """AI-generate an image for this variant via DALL-E 3 (OpenAI direct)."""
        from apps.media.serializers import MediaAssetSerializer
        from apps.media.services import (
            ImageGenerationError,
            generate_image_for_variant,
            has_openai_key,
        )

        variant = self.get_object()
        if not has_openai_key():
            return Response(
                {
                    "error": "openai_key_missing",
                    "message": (
                        "OPENAI_API_KEY is not configured. Add it to .env to enable AI image "
                        "generation. OpenRouter does not proxy DALL-E currently."
                    ),
                },
                status=503,
            )

        try:
            asset = generate_image_for_variant(
                variant=variant,
                brand=variant.post.brand,
                workspace=variant.post.workspace,
                user=request.user,
            )
        except ImageGenerationError as exc:
            return Response({"error": "generation_failed", "message": str(exc)}, status=502)

        # Attach to variant
        asset_url = request.build_absolute_uri(asset.url) if not asset.url.startswith(("http://", "https://")) else asset.url
        variant.media = [{
            "asset_id": str(asset.id),
            "type": "image",
            "url": asset_url,
            "alt": asset.alt_text,
            "width": asset.width,
            "height": asset.height,
            "source": "ai",
        }]
        variant.save(update_fields=["media", "updated_at"])

        return Response({
            "variant": PostVariantSerializer(variant).data,
            "asset": MediaAssetSerializer(asset, context={"request": request}).data,
        })


class ReferenceViewSet(_WorkspaceScopedViewSet):
    queryset = Reference.objects.all()
    serializer_class = ReferenceSerializer

    def perform_create(self, serializer) -> None:
        reference = serializer.save(
            workspace=self.request.workspace,
            added_by=self.request.user,
        )
        # Fire DNA extraction in the background. If the agent service is
        # unavailable, the reference still saves successfully.
        try:
            from apps.agent_runs.services import start_reference_dna

            start_reference_dna(reference=reference, user=self.request.user)
        except Exception:  # noqa: BLE001
            import logging

            logging.getLogger(__name__).warning(
                "Reference DNA auto-trigger failed for %s", reference.id, exc_info=True
            )

    @action(detail=True, methods=["post"], url_path="extract-dna")
    def extract_dna(self, request, id=None):  # noqa: A002,ARG002
        """Manually re-trigger DNA extraction for an existing Reference."""
        reference = self.get_object()
        from apps.agent_runs.services import start_reference_dna

        run = start_reference_dna(reference=reference, user=request.user)
        return Response({
            "agent_run_id": str(run.id),
            "reference_id": str(reference.id),
        })


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
