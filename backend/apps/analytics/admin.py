from django.contrib import admin

from .models import BanditArmState, MetricSnapshot


@admin.register(MetricSnapshot)
class MetricSnapshotAdmin(admin.ModelAdmin):
    list_display = ("publication", "captured_at", "impressions", "likes", "replies", "shares")
    list_filter = ("captured_at",)


@admin.register(BanditArmState)
class BanditArmStateAdmin(admin.ModelAdmin):
    list_display = ("variant", "campaign", "alpha", "beta", "successes", "trials")
