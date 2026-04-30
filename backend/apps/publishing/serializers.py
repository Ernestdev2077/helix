from __future__ import annotations

from rest_framework import serializers

from .models import PlatformAccount, Publication


class PlatformAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformAccount
        fields = (
            "id",
            "brand",
            "platform",
            "external_id",
            "handle",
            "display_name",
            "avatar_url",
            "status",
            "scopes",
            "created_at",
        )
        read_only_fields = fields


class PublicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Publication
        fields = (
            "id",
            "variant",
            "platform_account",
            "scheduled_for",
            "published_at",
            "external_id",
            "external_url",
            "status",
            "error_message",
            "retry_count",
            "created_at",
        )
        read_only_fields = (
            "id",
            "published_at",
            "external_id",
            "external_url",
            "error_message",
            "retry_count",
            "created_at",
        )
