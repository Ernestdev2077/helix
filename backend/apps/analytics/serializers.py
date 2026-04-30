from __future__ import annotations

from rest_framework import serializers

from .models import BanditArmState, MetricSnapshot


class MetricSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetricSnapshot
        fields = (
            "id",
            "publication",
            "captured_at",
            "impressions",
            "views",
            "likes",
            "replies",
            "shares",
            "saves",
            "clicks",
        )
        read_only_fields = fields


class BanditArmStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BanditArmState
        fields = (
            "id",
            "variant",
            "campaign",
            "alpha",
            "beta",
            "successes",
            "trials",
            "last_updated_at",
        )
        read_only_fields = fields
