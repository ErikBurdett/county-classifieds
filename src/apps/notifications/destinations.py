from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from django.urls import NoReverseMatch, reverse


@dataclass(frozen=True)
class DestinationSpec:
    required_kwargs: frozenset[str]


ALLOWED_DESTINATIONS: dict[str, DestinationSpec] = {
    "notifications:feed": DestinationSpec(required_kwargs=frozenset()),
    "listings:dashboard": DestinationSpec(required_kwargs=frozenset()),
    "listings:favorites": DestinationSpec(required_kwargs=frozenset()),
    "accounts:seller_profile": DestinationSpec(required_kwargs=frozenset()),
    "listings:owner_listing_detail": DestinationSpec(required_kwargs=frozenset({"listing_id"})),
}


def resolve_destination(*, route_name: str, route_kwargs: Mapping[str, Any]) -> str | None:
    """Resolve only a known internal route with a complete, UUID-safe argument set."""
    if not route_name:
        return None
    try:
        spec = ALLOWED_DESTINATIONS[route_name]
    except KeyError as error:
        raise ValueError("Unsupported notification destination.") from error

    if set(route_kwargs) != spec.required_kwargs:
        raise ValueError("Invalid notification destination arguments.")
    normalized_kwargs = {key: _normalize_uuid(value) for key, value in route_kwargs.items()}
    try:
        return reverse(route_name, kwargs=normalized_kwargs)
    except NoReverseMatch as error:
        raise ValueError("Invalid notification destination.") from error


def _normalize_uuid(value: Any) -> str:
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as error:
        raise ValueError("Invalid notification destination arguments.") from error
