from __future__ import annotations

from .catalog import ADS, AdCreative, AdSlot


def ads_for_slot(*, slot: AdSlot, limit: int | None = None) -> tuple[AdCreative, ...]:
    """Return a deterministic, deployment-managed creative collection."""
    creatives = tuple(ad for ad in ADS if ad.slot == slot)
    if slot == "inline":
        creatives = tuple(sorted(creatives, key=lambda ad: ad.id != "guerrilla-gear-inline"))
    return creatives if limit is None else creatives[:limit]


def partner_directory() -> tuple[tuple[AdCreative, ...], tuple[AdCreative, ...]]:
    """Deduplicate partners and split founding/internal from external partners."""
    seen: set[str] = set()
    partners: list[AdCreative] = []
    for ad in ADS:
        if ad.name in seen:
            continue
        seen.add(ad.name)
        partners.append(ad)
    nationwide = tuple(ad for ad in partners if not ad.is_internal)
    founding = tuple(ad for ad in partners if ad.is_internal)
    return nationwide, founding


def sponsor_for_scope(*, scope: str, offset: int = 0) -> AdCreative:
    """Choose a stable sponsor without adding cookie, account, or location tracking."""
    creatives = ads_for_slot(slot="inline")
    seed = 0
    for character in scope:
        seed = (seed * 31 + ord(character)) & 0xFFFFFFFF
    return creatives[(seed + offset) % len(creatives)]
