"""Seed a demo workspace + brand + a few references for the admin user.

Usage:
    python manage.py seed_demo
    python manage.py seed_demo --email someone@example.com
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.brands.models import Brand
from apps.content.models import Platform, Reference
from apps.workspaces.models import Membership, Workspace


class Command(BaseCommand):
    help = "Seed a demo workspace + brand + sample references."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--email", default="admin@helix.local")
        parser.add_argument("--workspace", default="helix-demo")
        parser.add_argument("--brand", default="helix")

    @transaction.atomic
    def handle(self, *args, **opts) -> None:
        User = get_user_model()
        email = opts["email"]
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"User {email} not found"))
            return

        workspace, ws_created = Workspace.objects.get_or_create(
            slug=opts["workspace"],
            defaults={"name": opts["workspace"].replace("-", " ").title(), "owner": user},
        )
        Membership.objects.get_or_create(
            workspace=workspace, user=user,
            defaults={"role": Membership.Role.OWNER},
        )

        brand, b_created = Brand.objects.get_or_create(
            workspace=workspace, slug=opts["brand"],
            defaults={
                "name": opts["brand"].title(),
                "description": "An agent-native SMM workspace that turns one brief into A/B-tested posts for X / Reddit / LinkedIn and continuously learns from likes and winners.",
                "voice_description": "Confident, technical, irreverent. Talks to indie devs and founders. Avoids corporate buzzwords.",
                "voice_do": ["use concrete numbers", "1 emoji max", "speak in first person", "show specific examples"],
                "voice_dont": ["synergy", "leverage", "unlock", "empower", "transform", "revolutionize"],
                "target_audience": "Indie hackers, dev-tool founders, B2B SaaS marketers shipping fast",
                "accent_color": "#7C3AED",
            },
        )

        seeds = [
            {
                "platform": Platform.X,
                "raw_text": (
                    "We replaced 6 different SaaS tools with 1 internal script.\n\n"
                    "Saved $4,200/year. Built it in an afternoon.\n\n"
                    "Stop renting what you can write."
                ),
                "tags": ["punchy", "numbers"],
                "likes_count": 5,
            },
            {
                "platform": Platform.LINKEDIN,
                "raw_text": (
                    "I shipped 3 SaaS products in the last 12 months.\n\n"
                    "Two failed. One has 800 paying customers.\n\n"
                    "Here is what the winner did differently:\n\n"
                    "1. It solved a problem I had myself, every single day\n"
                    "2. The first version took 11 days, not 3 months\n"
                    "3. We charged from day one — $19 from the very first user\n\n"
                    "If you can't sell version 0.1, version 1.0 won't save you."
                ),
                "tags": ["story", "first-person"],
                "likes_count": 8,
            },
            {
                "platform": Platform.REDDIT,
                "raw_text": (
                    "I'm a solo dev who burned $30k on a startup that nobody wanted.\n\n"
                    "Here is exactly what I'd do differently if I started over:\n\n"
                    "Validation isn't asking your friends. Validation is someone giving you $20 before you've written a line of code.\n\n"
                    "Talked to 50 'potential users' for my last project. 47 said it sounded great. 3 actually paid. Two of those refunded.\n\n"
                    "What worked the second time around: I posted my landing page in 3 niche subreddits and DMed everyone who upvoted. Got 14 paying customers in 4 days, before the product even existed.\n\n"
                    "Selling > building. Always."
                ),
                "tags": ["story", "founder-confessional"],
                "likes_count": 4,
            },
        ]
        created_refs = 0
        for s in seeds:
            _, made = Reference.objects.get_or_create(
                workspace=workspace, brand=brand,
                platform=s["platform"], raw_text=s["raw_text"],
                defaults={
                    "source": Reference.Source.PASTE,
                    "tags": s["tags"],
                    "likes_count": s["likes_count"],
                    "added_by": user,
                },
            )
            if made:
                created_refs += 1

        self.stdout.write(self.style.SUCCESS(
            f"workspace={'created' if ws_created else 'exists'} ({workspace.id}) "
            f"brand={'created' if b_created else 'exists'} ({brand.id}) "
            f"references_added={created_refs}"
        ))
        self.stdout.write(self.style.SUCCESS(f"\nLog in to UI as: {email}"))
        self.stdout.write(self.style.SUCCESS(f"Workspace ID: {workspace.id}"))
