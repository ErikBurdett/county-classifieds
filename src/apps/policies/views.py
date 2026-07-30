from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from .models import PolicyDocument, PolicyDocumentStatus


def document(request: HttpRequest, kind: str) -> HttpResponse:
    """Render only the current active policy text linked from seller acceptance."""
    policy = get_object_or_404(PolicyDocument, kind=kind, status=PolicyDocumentStatus.ACTIVE)
    return render(request, "policies/document.html", {"policy": policy})
