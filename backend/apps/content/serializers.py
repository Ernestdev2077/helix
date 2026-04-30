from __future__ import annotations

from rest_framework import serializers

from .models import Campaign, Post, PostVariant, Reference, StyleRule, WinningPattern


class CampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campaign
        fields = (
            "id",
            "brand",
            "name",
            "goal",
            "status",
            "starts_at",
            "ends_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class PostVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostVariant
        fields = (
            "id",
            "post",
            "platform",
            "label",
            "content",
            "media",
            "status",
            "is_starred",
            "allocation_weight",
            "critic_notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "allocation_weight", "critic_notes", "created_at", "updated_at")


class PostSerializer(serializers.ModelSerializer):
    variants = PostVariantSerializer(many=True, read_only=True)

    class Meta:
        model = Post
        fields = (
            "id",
            "brand",
            "campaign",
            "brief",
            "goals",
            "tone_hints",
            "target_platforms",
            "status",
            "pinned_reference_ids",
            "variants",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "status", "variants", "created_at", "updated_at")


class ReferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reference
        fields = (
            "id",
            "brand",
            "platform",
            "source",
            "source_url",
            "raw_text",
            "media",
            "tags",
            "source_metrics",
            "extracted_features",
            "likes_count",
            "use_count",
            "created_at",
        )
        read_only_fields = (
            "id",
            "extracted_features",
            "use_count",
            "created_at",
        )


class StyleRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = StyleRule
        fields = (
            "id",
            "brand",
            "scope",
            "platform",
            "campaign",
            "rule_text",
            "rationale",
            "confidence",
            "status",
            "version",
            "created_at",
            "reviewed_at",
        )
        read_only_fields = (
            "id",
            "confidence",
            "version",
            "created_at",
            "reviewed_at",
        )


class WinningPatternSerializer(serializers.ModelSerializer):
    class Meta:
        model = WinningPattern
        fields = (
            "id",
            "brand",
            "platform",
            "pattern_text",
            "metric",
            "lift",
            "sample_size",
            "confidence_interval",
            "promoted_to_rule",
            "created_at",
        )
        read_only_fields = fields
