from django.contrib import admin

from .models import CreditLedger, Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("workspace", "status", "seats", "current_period_end")
    list_filter = ("status",)


@admin.register(CreditLedger)
class CreditLedgerAdmin(admin.ModelAdmin):
    list_display = ("workspace", "kind", "amount", "agent_run", "created_at")
    list_filter = ("kind",)
