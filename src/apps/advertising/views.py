from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from .selectors import partner_directory


def partners(request: HttpRequest) -> HttpResponse:
    nationwide_partners, founding_partners = partner_directory()
    return render(
        request,
        "advertising/partners.html",
        {
            "nationwide_partners": nationwide_partners,
            "founding_partners": founding_partners,
        },
    )
