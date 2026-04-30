from __future__ import annotations

from rest_framework.routers import DefaultRouter

from .views import InviteViewSet, WorkspaceViewSet

router = DefaultRouter()
router.register(r"invites", InviteViewSet, basename="invite")
router.register(r"", WorkspaceViewSet, basename="workspace")

urlpatterns = router.urls
