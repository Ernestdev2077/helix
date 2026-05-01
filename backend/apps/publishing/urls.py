from __future__ import annotations

from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views
from .views import PlatformAccountViewSet, PublicationViewSet

router = DefaultRouter()
router.register(r"accounts", PlatformAccountViewSet, basename="platformaccount")
router.register(r"publications", PublicationViewSet, basename="publication")

urlpatterns = [
    path("oauth-status/", views.oauth_status, name="oauth-status"),
    *router.urls,
]
