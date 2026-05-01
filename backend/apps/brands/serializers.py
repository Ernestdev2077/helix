from __future__ import annotations

from rest_framework import serializers

from .models import Brand, KBDocument


class BrandSerializer(serializers.ModelSerializer):
    slug = serializers.SlugField(required=False, allow_blank=True, max_length=60)

    class Meta:
        model = Brand
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "voice_description",
            "voice_do",
            "voice_dont",
            "target_audience",
            "personas",
            "accent_color",
            "logo_url",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class KBDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = KBDocument
        fields = (
            "id",
            "brand",
            "title",
            "source_type",
            "source_uri",
            "mime_type",
            "status",
            "error_message",
            "token_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "status",
            "error_message",
            "token_count",
            "created_at",
            "updated_at",
        )
