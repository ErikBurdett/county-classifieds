from __future__ import annotations

from dataclasses import dataclass

from django.http import HttpRequest
from django.urls import reverse

from apps.listings.models import Listing, ListingImage, ListingImageState

from .models import County, State


@dataclass(frozen=True)
class PublicPageMetadata:
    """Safe, template-ready metadata for an already-public page."""

    title: str
    description: str
    canonical_url: str
    robots: str | None = None
    image_url: str | None = None
    image_width: int | None = None
    image_height: int | None = None


def _absolute_url(*, request: HttpRequest, path: str) -> str:
    """Build a site URL through Django's validated request host and scheme."""
    return request.build_absolute_uri(path)


def home_metadata(*, request: HttpRequest) -> PublicPageMetadata:
    return PublicPageMetadata(
        title="Regional marketplace | TheCountyPost Market",
        description="Browse public regional listings by state and county on TheCountyPost Market.",
        canonical_url=_absolute_url(request=request, path=reverse("core:home")),
    )


def market_finder_metadata(*, request: HttpRequest) -> PublicPageMetadata:
    return PublicPageMetadata(
        title="Find a market | TheCountyPost Market",
        description="Find an active state or county market on TheCountyPost Market.",
        canonical_url=_absolute_url(request=request, path=reverse("locations:market_finder")),
        robots="noindex,follow",
    )


def directory_metadata(
    *, request: HttpRequest, state: State, county: County | None = None
) -> PublicPageMetadata:
    path = (
        reverse(
            "locations:county_context",
            kwargs={"state_slug": state.slug, "county_slug": county.slug},
        )
        if county is not None
        else reverse("locations:state_context", kwargs={"state_slug": state.slug})
    )
    location = f"{county.name}, {state.name}" if county is not None else state.name
    return PublicPageMetadata(
        title=f"Listings in {location} | TheCountyPost Market",
        description=f"Browse public listings in {location} on TheCountyPost Market.",
        canonical_url=_absolute_url(request=request, path=path),
        robots="noindex,follow" if request.GET else None,
    )


def listing_metadata(
    *, request: HttpRequest, listing: Listing, image: ListingImage | None
) -> PublicPageMetadata:
    path = reverse(
        "locations:listing_detail",
        kwargs={
            "state_slug": listing.state.slug,
            "county_slug": listing.county.slug,
            "listing_id": listing.id,
        },
    )
    image_url: str | None = None
    image_width: int | None = None
    image_height: int | None = None
    if (
        image is not None
        and image.state == ListingImageState.READY
        and bool(image.rendition_key)
        and image.width > 0
        and image.height > 0
    ):
        image_url = _absolute_url(
            request=request,
            path=reverse("locations:public_listing_image", kwargs={"image_id": image.id}),
        )
        image_width = image.width
        image_height = image.height
    return PublicPageMetadata(
        title=f"{listing.title} | TheCountyPost Market",
        description=(
            f"{listing.title} in {listing.city}, {listing.state.name}. "
            "Browse this public listing on TheCountyPost Market."
        ),
        canonical_url=_absolute_url(request=request, path=path),
        image_url=image_url,
        image_width=image_width,
        image_height=image_height,
    )
