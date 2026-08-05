from __future__ import annotations

from collections.abc import Iterator
from xml.sax.saxutils import escape

from django.db import connection
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBase,
    JsonResponse,
    StreamingHttpResponse,
)
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from apps.advertising.selectors import ads_for_slot
from apps.listings.presenters import present_public_listing
from apps.listings.selectors import public_listing_with_images, public_listings
from apps.locations.forms import PublicMarketFinderForm
from apps.locations.models import County, State
from apps.locations.presentation import home_metadata

SITEMAP_PAGE_SIZE = 1_000


def page_not_found(request: HttpRequest, exception: Exception | None = None) -> HttpResponse:
    """Render a generic branded 404 without disclosing the failed path."""
    del exception
    return render(request, "404.html", status=404)


def _absolute_url(request: HttpRequest, path: str) -> str:
    return request.build_absolute_uri(path)


def _xml_response(rows: Iterator[str]) -> StreamingHttpResponse:
    response = StreamingHttpResponse(rows, content_type="application/xml; charset=utf-8")
    response["X-Robots-Tag"] = "noindex"
    return response


def _urlset(rows: Iterator[str]) -> Iterator[str]:
    yield '<?xml version="1.0" encoding="UTF-8"?>\n'
    yield '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    yield from rows
    yield "</urlset>\n"


@require_GET
def home(request: HttpRequest) -> HttpResponse:
    listings = list(public_listing_with_images().order_by("-published_at")[:6])
    return render(
        request,
        "home.html",
        {
            "seo_metadata": home_metadata(request=request),
            "states": State.objects.filter(is_active=True),
            "location_finder_form": PublicMarketFinderForm(),
            "inline_ads": ads_for_slot(slot="inline", limit=8),
            "listing_ads": ads_for_slot(slot="inline", limit=3),
            "listings": listings,
            "listing_cards": [
                {
                    "listing": listing,
                    "presentation": present_public_listing(listing=listing),
                    "image": next(iter(listing.images.all()), None),
                }
                for listing in listings
            ],
        },
    )


@require_GET
def robots(request: HttpRequest) -> HttpResponse:
    sitemap_url = _absolute_url(request, reverse("core:sitemap_index"))
    return HttpResponse(
        f"User-agent: *\nAllow: /\nDisallow: /admin/\nDisallow: /dashboard/\n"
        f"Disallow: /staff/\nDisallow: /billing/\nDisallow: /favorites/\nSitemap: {sitemap_url}\n",
        content_type="text/plain; charset=utf-8",
    )


@require_GET
def sitemap_index(request: HttpRequest) -> StreamingHttpResponse:
    def rows() -> Iterator[str]:
        yield '<?xml version="1.0" encoding="UTF-8"?>\n'
        yield '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        for name in ("states", "counties", "listings"):
            count = {
                "states": State.objects.filter(is_active=True, is_network_enabled=True).count(),
                "counties": County.objects.filter(
                    is_active=True,
                    is_network_enabled=True,
                    state__is_active=True,
                    state__is_network_enabled=True,
                ).count(),
                "listings": public_listings().count(),
            }[name]
            for page_number in range(
                1, max(1, (count + SITEMAP_PAGE_SIZE - 1) // SITEMAP_PAGE_SIZE) + 1
            ):
                path = reverse("core:sitemap_page", kwargs={"section": name, "page": page_number})
                yield f"<sitemap><loc>{escape(_absolute_url(request, path))}</loc></sitemap>\n"
        yield "</sitemapindex>\n"

    return _xml_response(rows())


@require_GET
def sitemap_page(request: HttpRequest, section: str, page: int) -> HttpResponseBase:
    paths: Iterator[str]
    if section == "states":
        state_slugs = (
            State.objects.filter(is_active=True, is_network_enabled=True)
            .order_by("id")
            .values_list("slug", flat=True)
        )
        paths = (
            reverse("locations:state_context", kwargs={"state_slug": slug})
            for slug in state_slugs[(page - 1) * SITEMAP_PAGE_SIZE : page * SITEMAP_PAGE_SIZE]
        )
    elif section == "counties":
        county_slugs = (
            County.objects.filter(
                is_active=True,
                is_network_enabled=True,
                state__is_active=True,
                state__is_network_enabled=True,
            )
            .order_by("id")
            .values_list("state__slug", "slug")
        )
        paths = (
            reverse(
                "locations:county_context",
                kwargs={"state_slug": state_slug, "county_slug": county_slug},
            )
            for state_slug, county_slug in county_slugs[
                (page - 1) * SITEMAP_PAGE_SIZE : page * SITEMAP_PAGE_SIZE
            ]
        )
    elif section == "listings":
        listing_locations = (
            public_listings().order_by("id").values_list("state__slug", "county__slug", "id")
        )
        paths = (
            reverse(
                "locations:listing_detail",
                kwargs={
                    "state_slug": state_slug,
                    "county_slug": county_slug,
                    "listing_id": listing_id,
                },
            )
            for state_slug, county_slug, listing_id in listing_locations[
                (page - 1) * SITEMAP_PAGE_SIZE : page * SITEMAP_PAGE_SIZE
            ]
        )
    else:
        return HttpResponse(status=404)

    return _xml_response(
        _urlset(f"<url><loc>{escape(_absolute_url(request, path))}</loc></url>\n" for path in paths)
    )


@never_cache
@require_GET
def liveness(_request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok"})


@never_cache
@require_GET
def readiness(_request: HttpRequest) -> JsonResponse:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:  # noqa: BLE001 - the health boundary must not leak database failures
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ready"})
