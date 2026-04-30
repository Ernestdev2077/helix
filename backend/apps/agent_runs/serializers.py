from __future__ import annotations

from rest_framework import serializers

from .models import AgentEvent, AgentRun


class AgentEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentEvent
        fields = (
            "id",
            "sequence",
            "kind",
            "node_name",
            "message",
            "data",
            "tokens_in",
            "tokens_out",
            "duration_ms",
            "created_at",
        )
        read_only_fields = fields


class AgentRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentRun
        fields = (
            "id",
            "kind",
            "status",
            "post",
            "input_payload",
            "output_payload",
            "error_message",
            "started_at",
            "finished_at",
            "total_tokens_in",
            "total_tokens_out",
            "total_cost_usd",
            "created_at",
        )
        read_only_fields = fields
