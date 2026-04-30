from __future__ import annotations

from rest_framework.routers import DefaultRouter

from .views import PlatformAccountViewSet, PublicationViewSet

router = DefaultRouter()
router.register(r"accounts", PlatformAccountViewSet, basename="platformaccount")
router.register(r"publications", PublicationViewSet, basename="publication")

urlpatterns = router.urls
