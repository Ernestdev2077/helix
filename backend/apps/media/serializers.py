from __future__ import annotations

from rest_framework import serializers

from .models import MediaAsset


class MediaAssetSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = MediaAsset
        fields = (
            "id",
            "url",
            "source",
            "mime_type",
            "width",
            "height",
            "size_bytes",
            "alt_text",
            "ai_prompt",
            "ai_model",
            "cost_usd",
            "created_at",
        )
        read_only_fields = fields

    def get_url(self, obj: MediaAsset) -> str:
        request = self.context.get("request")
        raw = obj.url
        if request and raw and not raw.startswith(("http://", "https://")):
            return request.build_absolute_uri(raw)
        return raw
