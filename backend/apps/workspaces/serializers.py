from __future__ import annotations

from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from .models import Invite, Membership, Workspace


class WorkspaceSerializer(serializers.ModelSerializer):
    my_role = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = (
            "id",
            "name",
            "slug",
            "plan",
            "trial_ends_at",
            "ai_credits_monthly",
            "ai_credits_used",
            "created_at",
            "my_role",
        )
        read_only_fields = (
            "id",
            "slug",
            "plan",
            "ai_credits_monthly",
            "ai_credits_used",
            "created_at",
            "my_role",
        )

    def get_my_role(self, obj: Workspace) -> str | None:
        user = self.context["request"].user
        membership = obj.memberships.filter(user=user).first()
        return membership.role if membership else None


class MembershipSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    full_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = Membership
        fields = ("id", "email", "full_name", "role", "created_at")
        read_only_fields = ("id", "email", "full_name", "created_at")


class InviteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invite
        fields = (
            "id",
            "email",
            "role",
            "status",
            "expires_at",
            "created_at",
        )
        read_only_fields = ("id", "status", "expires_at", "created_at")

    def create(self, validated_data):
        workspace = self.context["workspace"]
        user = self.context["request"].user
        validated_data["workspace"] = workspace
        validated_data["invited_by"] = user
        validated_data.setdefault("expires_at", timezone.now() + timedelta(days=7))
        return super().create(validated_data)
