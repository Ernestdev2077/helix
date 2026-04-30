"""Mixins that auto-scope querysets to the active workspace."""

from __future__ import annotations


class WorkspaceScopedMixin:
    """Restrict queryset to objects belonging to the active workspace.

    Assumes the model has a ``workspace`` FK (directly or via a related path
    configured as ``workspace_lookup``).
    """

    workspace_lookup: str = "workspace"

    def get_queryset(self):  # type: ignore[override]
        qs = super().get_queryset()  # type: ignore[misc]
        workspace = getattr(self.request, "workspace", None)
        if workspace is None:
            return qs.none()
        return qs.filter(**{self.workspace_lookup: workspace})

    def perform_create(self, serializer) -> None:  # type: ignore[override]
        serializer.save(workspace=self.request.workspace)
