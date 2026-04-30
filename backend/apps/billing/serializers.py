from __future__ import annotations

from rest_framework import serializers

from .models import CreditLedger, Subscription


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = (
            "id",
            "stripe_subscription_id",
            "stripe_price_id",
            "seats",
            "status",
            "current_period_start",
            "current_period_end",
            "cancel_at_period_end",
        )
        read_only_fields = fields


class CreditLedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditLedger
        fields = ("id", "kind", "amount", "agent_run", "memo", "created_at")
        read_only_fields = fields
