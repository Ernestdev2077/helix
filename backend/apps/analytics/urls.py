from __future__ import annotations

from rest_framework.routers import DefaultRouter

from .views import BanditArmStateViewSet, MetricSnapshotViewSet

router = DefaultRouter()
router.register(r"metrics", MetricSnapshotViewSet, basename="metricsnapshot")
router.register(r"bandit", BanditArmStateViewSet, basename="banditarmstate")

urlpatterns = router.urls
