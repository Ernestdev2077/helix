"""Root URL configuration."""

from __future__ import annotations

from django.conf import settings
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health(_request):
    """Liveness probe — not auth-gated."""
    return JsonResponse({"status": "ok", "service": "helix-backend"})


from apps.publishing.views import x_oauth_callback, x_oauth_start

api_patterns = [
    path("auth/", include("dj_rest_auth.urls")),
    path("auth/registration/", include("dj_rest_auth.registration.urls")),
    path("auth/social/", include("allauth.socialaccount.urls")),
    path("auth/oauth/x/start/", x_oauth_start, name="oauth-x-start"),
    path("auth/oauth/x/callback/", x_oauth_callback, name="oauth-x-callback"),
    path("workspaces/", include("apps.workspaces.urls")),
    path("brands/", include("apps.brands.urls")),
    path("content/", include("apps.content.urls")),
    path("media/", include("apps.media.urls")),
    path("publishing/", include("apps.publishing.urls")),
    path("analytics/", include("apps.analytics.urls")),
    path("agent-runs/", include("apps.agent_runs.urls")),
    path("billing/", include("apps.billing.urls")),
]

urlpatterns = [
    path("health/", health, name="health"),
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("api/v1/", include((api_patterns, "api"), namespace="api")),
]

if settings.DEBUG:
    from django.conf.urls.static import static

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    try:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls)), *urlpatterns]
    except ImportError:
        pass
