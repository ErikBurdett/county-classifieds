"""Public-safe PostgreSQL search document construction and query helpers."""

from __future__ import annotations

from typing import Any

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db import connection
from django.db.models import F, Q, QuerySet, Value

from apps.catalog.models import CatalogPostingField, PostingFieldVisibility

from .models import Listing

SEARCH_CONFIG = "english"
SEARCH_RANK_WEIGHTS = [0.1, 0.2, 0.4, 1.0]


def postgres_search_available() -> bool:
    return connection.vendor == "postgresql"


def _display(instance: object, field: str) -> str:
    value = getattr(instance, f"get_{field}_display", None)
    return str(value()) if callable(value) else str(getattr(instance, field, "") or "")


def public_search_terms(listing: Listing) -> dict[str, list[str]]:
    """Return only approved text; never add private aggregate fields here."""

    terms = {
        "A": [listing.title],
        "B": [
            listing.category.name,
            listing.vertical.name,
            *(tag.category.name for tag in listing.controlled_tags.all()),
            *(tag.value for tag in listing.seller_tags.all()),
        ],
        "C": [listing.city],
        "D": [listing.description],
    }
    if hasattr(listing, "auto_details"):
        auto_details = listing.auto_details
        terms["B"] += [auto_details.make, auto_details.model, auto_details.trim]
    elif hasattr(listing, "ag_equipment_details"):
        equipment_details = listing.ag_equipment_details
        terms["B"] += [
            equipment_details.make,
            equipment_details.model,
            _display(equipment_details, "equipment_type"),
        ]
    elif hasattr(listing, "home_goods_details"):
        goods_details = listing.home_goods_details
        terms["B"] += [goods_details.brand, goods_details.item_type]
    elif hasattr(listing, "livestock_details"):
        livestock_details = listing.livestock_details
        terms["B"] += [
            _display(livestock_details, "species"),
            livestock_details.breed,
            livestock_details.animal_class,
        ]
    elif hasattr(listing, "home_details"):
        terms["B"].append(_display(listing.home_details, "property_type"))
    elif hasattr(listing, "rental_details"):
        terms["B"].append(_display(listing.rental_details, "rental_type"))
    elif hasattr(listing, "pasture_details"):
        pasture_details = listing.pasture_details
        terms["B"] += [
            f"{pasture_details.acreage} acres",
            "water available" if pasture_details.water_available else "",
            "fenced" if pasture_details.fenced else "",
            pasture_details.lease_term,
        ]
    elif hasattr(listing, "generic_details"):
        try:
            profile = listing.category.posting_profile
        except AttributeError:
            profile = None
        if profile is not None:
            allowed = {
                field.key
                for field in profile.fields.all()
                if field.visibility == PostingFieldVisibility.PUBLIC and field.allow_public_search
            }
            terms["B"] += [
                str(value)
                for key, value in listing.generic_details.attributes.items()
                if key in allowed and isinstance(value, (str, int))
            ]
    return {
        weight: [term.strip() for term in values if term and term.strip()]
        for weight, values in terms.items()
    }


def public_search_vector(listing: Listing) -> Any:
    """Build the weighted database expression without ever reading private fields."""

    vectors = [
        SearchVector(Value(" ".join(terms)), config=SEARCH_CONFIG, weight=weight)
        for weight, terms in public_search_terms(listing).items()
        if terms
    ]
    if not vectors:
        return SearchVector(Value(""), config=SEARCH_CONFIG)
    expression: Any = vectors[0]
    for vector in vectors[1:]:
        expression = expression + vector
    return expression


def rebuild_public_search_document(*, listing: Listing) -> None:
    """Persist a safe document before a listing can become publicly visible."""

    if not postgres_search_available():
        return
    Listing.objects.filter(pk=listing.pk).update(search_document=public_search_vector(listing))


def apply_text_search(queryset: QuerySet[Listing], query: str) -> QuerySet[Listing]:
    """Apply PostgreSQL FTS or a bounded SQLite-compatible safe fallback."""

    query = query.strip()
    if not query:
        return queryset
    if postgres_search_available():
        search_query = SearchQuery(query, config=SEARCH_CONFIG, search_type="websearch")
        return queryset.filter(search_document=search_query).annotate(
            search_rank=SearchRank(F("search_document"), search_query, weights=SEARCH_RANK_WEIGHTS)
        )
    generic_conditions = Q()
    for field in CatalogPostingField.objects.filter(
        visibility=PostingFieldVisibility.PUBLIC, allow_public_search=True
    ).select_related("profile__category"):
        generic_conditions |= Q(
            category_id=field.profile.category_id,
            **{f"generic_details__attributes__{field.key}__icontains": query},
        )
    return queryset.filter(
        Q(title__icontains=query)
        | Q(description__icontains=query)
        | Q(city__icontains=query)
        | Q(category__name__icontains=query)
        | Q(vertical__name__icontains=query)
        | Q(controlled_tags__category__name__icontains=query)
        | Q(seller_tags__value__icontains=query)
        | Q(auto_details__make__icontains=query)
        | Q(auto_details__model__icontains=query)
        | Q(ag_equipment_details__make__icontains=query)
        | Q(ag_equipment_details__model__icontains=query)
        | Q(home_goods_details__brand__icontains=query)
        | Q(home_goods_details__item_type__icontains=query)
        | Q(livestock_details__breed__icontains=query)
        | Q(livestock_details__animal_class__icontains=query)
        | generic_conditions
    ).distinct()
