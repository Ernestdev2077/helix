from __future__ import annotations

from rest_framework.routers import DefaultRouter

from .views import CreditLedgerViewSet, SubscriptionViewSet

router = DefaultRouter()
router.register(r"subscription", SubscriptionViewSet, basename="subscription")
router.register(r"credits", CreditLedgerViewSet, basename="creditledger")

urlpatterns = router.urls
