from __future__ import annotations

from rest_framework.routers import DefaultRouter

from .views import BrandViewSet, KBDocumentViewSet

router = DefaultRouter()
router.register(r"documents", KBDocumentViewSet, basename="kbdocument")
router.register(r"", BrandViewSet, basename="brand")

urlpatterns = router.urls
