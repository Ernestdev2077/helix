from __future__ import annotations

from rest_framework.routers import DefaultRouter

from .views import AgentRunViewSet

router = DefaultRouter()
router.register(r"", AgentRunViewSet, basename="agentrun")

urlpatterns = router.urls
