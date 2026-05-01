from __future__ import annotations

from django.urls import path
from rest_framework.routers import DefaultRouter

from . import internal_views
from .views import AgentRunViewSet

router = DefaultRouter()
router.register(r"", AgentRunViewSet, basename="agentrun")

urlpatterns = [
    path("internal/content-completed/", internal_views.content_completed),
    path("internal/curation-completed/", internal_views.curation_completed),
    path("internal/reference-dna-completed/", internal_views.reference_dna_completed),
    path("internal/emit-event/", internal_views.emit_event),
    *router.urls,
]
