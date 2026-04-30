from __future__ import annotations

from rest_framework.routers import DefaultRouter

from .views import (
    CampaignViewSet,
    PostVariantViewSet,
    PostViewSet,
    ReferenceViewSet,
    StyleRuleViewSet,
    WinningPatternViewSet,
)

router = DefaultRouter()
router.register(r"campaigns", CampaignViewSet, basename="campaign")
router.register(r"posts", PostViewSet, basename="post")
router.register(r"variants", PostVariantViewSet, basename="variant")
router.register(r"references", ReferenceViewSet, basename="reference")
router.register(r"style-rules", StyleRuleViewSet, basename="stylerule")
router.register(r"winning-patterns", WinningPatternViewSet, basename="winningpattern")

urlpatterns = router.urls
