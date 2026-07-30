from __future__ import annotations

from django.db.models import Q, QuerySet

from .models import County, State


def get_active_state_by_slug(*, state_slug: str) -> State | None:
    return (
        State.objects.filter(
            slug=state_slug,
            is_active=True,
        )
        .only("id", "name", "slug")
        .first()
    )


def get_active_county_by_slugs(*, state_slug: str, county_slug: str) -> County | None:
    return (
        County.objects.select_related("state")
        .filter(
            slug=county_slug,
            is_active=True,
            state__slug=state_slug,
            state__is_active=True,
        )
        .only("id", "name", "slug", "state__id", "state__name", "state__slug")
        .first()
    )


def find_active_markets(*, query: str) -> tuple[QuerySet[State], QuerySet[County]]:
    """Return active directory records matching a free-text market lookup."""
    query = query.strip()
    if not query:
        return State.objects.none(), County.objects.none()
    terms = query.split()
    state_matches = State.objects.filter(is_active=True)
    county_matches = County.objects.filter(is_active=True, state__is_active=True)
    for term in terms:
        state_matches = state_matches.filter(
            Q(name__icontains=term) | Q(usps_code__iexact=term) | Q(slug__icontains=term)
        )
        county_matches = county_matches.filter(
            Q(name__icontains=term)
            | Q(slug__icontains=term)
            | Q(state__name__icontains=term)
            | Q(state__usps_code__iexact=term)
        )
    return state_matches.order_by("name"), county_matches.select_related("state").order_by(
        "state__name", "name"
    )
