from __future__ import annotations

from urllib.parse import urlencode
from uuid import UUID

from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.cache import patch_vary_headers
from django.views.decorators.http import require_GET

from apps.listings.models import ListingImage, ListingImageState
from apps.listings.presenters import present_public_listing
from apps.listings.selectors import (
    public_listing_for_location,
    public_listing_with_images,
    public_listings,
    public_listings_near_county,
)

from .forms import PublicBrowseForm, PublicMarketFinderForm, apply_public_filters
from .models import County, State
from .presentation import directory_metadata, listing_metadata, market_finder_metadata
from .selectors import (
    find_active_markets,
    get_active_county_by_slugs,
    get_active_state_by_slug,
)


def _canonical_redirect(request: HttpRequest, path: str) -> HttpResponse:
    query = request.GET.copy()
    if query.get("page") == "1":
        query.pop("page")
    query_string = query.urlencode()
    if query_string:
        path = f"{path}?{query_string}"
    response = HttpResponse(status=301)
    response["Location"] = path
    return response


def _is_fragment_request(request: HttpRequest) -> bool:
    return request.headers.get("Accept") == "text/vnd.countypost.fragment+html"


def _query_url(*, path: str, parameters: list[tuple[str, str]]) -> str:
    query = urlencode(parameters)
    return f"{path}?{query}" if query else path


def _browse_context(
    *,
    request: HttpRequest,
    state: State,
    county: County | None = None,
) -> dict[str, object]:
    is_county = county is not None
    form = PublicBrowseForm(
        request.GET,
        state=state,
        fixed_county=county,
    )
    listings = public_listing_with_images().filter(state=state)
    if county is not None and form.is_valid() and form.cleaned_data["scope"] == "county":
        listings = listings.filter(
            Q(county=county) | Q(additional_counties__county=county)
        ).distinct()
    listings = apply_public_filters(listings, form) if form.is_valid() else listings
    page = Paginator(listings, 24).get_page(request.GET.get("page"))
    filter_chips = [
        {
            "label": label,
            "url": _query_url(
                path=request.path,
                parameters=form.query_parameters(exclude=frozenset({name})),
            ),
        }
        for name, label in form.active_filter_labels()
    ]
    reset_parameters = form.query_parameters(
        exclude=frozenset(form.fields) - {"nearby_radius", "scope"},
    )
    context: dict[str, object] = {
        "state": state,
        "county": county,
        "browse_form": form,
        "filter_chips": filter_chips,
        "filter_clear_all_url": request.path,
        "filter_reset_url": _query_url(path=request.path, parameters=reset_parameters),
        "filter_disclosure_open": bool(form.query_parameters() or form.errors),
        "pagination_query": urlencode(form.query_parameters()),
        "page_obj": page,
        "listing_cards": [
            {
                "listing": listing,
                "presentation": present_public_listing(listing=listing),
                "image": next(iter(listing.images.all()), None),
            }
            for listing in page.object_list
        ],
        "is_county": is_county,
        "seo_metadata": directory_metadata(request=request, state=state, county=county),
    }
    if (
        county is not None
        and county.centroid_latitude is not None
        and county.centroid_longitude is not None
        and form.is_valid()
    ):
        radius = form.cleaned_data.get("nearby_radius") or 50
        nearby_listings = public_listings_near_county(county=county, radius_miles=radius)
        context.update(
            {
                "nearby_radius": radius,
                "nearby_rail_available": True,
                "nearby_listing_cards": [
                    {
                        "listing": listing,
                        "presentation": present_public_listing(listing=listing),
                        "image": None,
                        "distance_miles": round(float(listing.__dict__["nearby_distance_miles"])),
                    }
                    for listing in nearby_listings
                ],
            }
        )
    return context


def _browse_response(*, request: HttpRequest, context: dict[str, object]) -> HttpResponse:
    is_fragment = _is_fragment_request(request)
    template_name = "locations/_browse_results.html" if is_fragment else "locations/browse.html"
    form = context["browse_form"]
    assert isinstance(form, PublicBrowseForm)
    response = render(
        request,
        template_name,
        context,
        status=400 if is_fragment and not form.is_valid() else 200,
    )
    patch_vary_headers(response, ("Accept",))
    return response


@require_GET
def market_finder(request: HttpRequest) -> HttpResponse:
    """Search the active nationwide directory."""

    form = PublicMarketFinderForm(request.GET)
    context: dict[str, object] = {
        "location_finder_form": form,
        "seo_metadata": market_finder_metadata(request=request),
    }
    status = 200
    if form.is_valid():
        states, counties = find_active_markets(query=form.cleaned_data["q"])
        context.update(
            {
                "market_states": states,
                "market_counties": counties,
                "market_search_performed": bool(form.cleaned_data["q"].strip()),
            }
        )
    else:
        status = 400
    template_name = (
        "locations/_market_results.html"
        if _is_fragment_request(request)
        else "locations/market_finder.html"
    )
    response = render(request, template_name, context, status=status)
    patch_vary_headers(response, ("Accept",))
    return response


@require_GET
def state_context(request: HttpRequest, state_slug: str) -> HttpResponse:
    canonical_state_slug = state_slug.lower()
    state = get_active_state_by_slug(state_slug=canonical_state_slug)
    if state is None:
        return render(request, "404.html", status=404)
    if state_slug != canonical_state_slug:
        return _canonical_redirect(
            request,
            reverse("locations:state_context", kwargs={"state_slug": canonical_state_slug}),
        )
    context = _browse_context(request=request, state=state)
    context.update(
        {
            "location_finder_form": PublicMarketFinderForm(),
            "counties": state.counties.filter(is_active=True, is_network_enabled=True).annotate(
                public_listing_count=Count(
                    "listings",
                    filter=(
                        Q(listings__status="published")
                        & Q(listings__vertical__is_active=True)
                        & Q(listings__category__is_active=True)
                    ),
                )
            ),
        }
    )
    return _browse_response(request=request, context=context)


@require_GET
def county_context(request: HttpRequest, state_slug: str, county_slug: str) -> HttpResponse:
    canonical_state_slug = state_slug.lower()
    canonical_county_slug = county_slug.lower()
    county = get_active_county_by_slugs(
        state_slug=canonical_state_slug,
        county_slug=canonical_county_slug,
    )
    if county is None:
        return render(request, "404.html", status=404)
    if (state_slug, county_slug) != (canonical_state_slug, canonical_county_slug):
        return _canonical_redirect(
            request,
            reverse(
                "locations:county_context",
                kwargs={
                    "state_slug": canonical_state_slug,
                    "county_slug": canonical_county_slug,
                },
            ),
        )
    context = _browse_context(request=request, state=county.state, county=county)
    context["location_finder_form"] = PublicMarketFinderForm()
    return _browse_response(request=request, context=context)


@require_GET
def listing_detail(
    request: HttpRequest, state_slug: str, county_slug: str, listing_id: UUID
) -> HttpResponse:
    listing = public_listing_for_location(
        listing_id=listing_id, state_slug=state_slug.lower(), county_slug=county_slug.lower()
    )
    if (state_slug, county_slug) != (state_slug.lower(), county_slug.lower()):
        return _canonical_redirect(
            request,
            reverse(
                "locations:listing_detail",
                kwargs={
                    "state_slug": listing.state.slug,
                    "county_slug": listing.county.slug,
                    "listing_id": listing.id,
                },
            ),
        )
    if county_slug.lower() != listing.county.slug:
        return _canonical_redirect(
            request,
            reverse(
                "locations:listing_detail",
                kwargs={
                    "state_slug": listing.state.slug,
                    "county_slug": listing.county.slug,
                    "listing_id": listing.id,
                },
            ),
        )
    images = list(listing.images.all())
    return render(
        request,
        "locations/listing_detail.html",
        {
            "listing": listing,
            "presentation": present_public_listing(listing=listing),
            "images": images,
            "seo_metadata": listing_metadata(
                request=request,
                listing=listing,
                image=images[0] if images else None,
            ),
        },
    )


@require_GET
def public_listing_image(_request: HttpRequest, image_id: UUID) -> FileResponse:
    try:
        image = (
            ListingImage.objects.filter(
                pk=image_id,
                state=ListingImageState.READY,
                listing__in=public_listings(),
            )
            .only("id", "content_type", "rendition_key")
            .get()
        )
    except ListingImage.DoesNotExist as error:
        raise Http404("Image not found.") from error
    response = FileResponse(
        default_storage.open(image.rendition_key, "rb"), content_type=image.content_type
    )
    response["Cache-Control"] = "public, max-age=3600"
    response["Content-Disposition"] = "inline"
    return response
