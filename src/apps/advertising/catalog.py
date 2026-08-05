from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

AdSlot = Literal["inline", "banner"]
PARTNER_DIRECTORY_PATH = "/partners/"


@dataclass(frozen=True)
class AdCreative:
    id: str
    slot: AdSlot
    image_name: str
    name: str
    alt: str
    href: str

    @property
    def is_internal(self) -> bool:
        return self.href == PARTNER_DIRECTORY_PATH


ADS: tuple[AdCreative, ...] = (
    AdCreative(
        "lemc-inline",
        "inline",
        "LEMC250.jpg",
        "LEMC Realty",
        "LEMC Realty",
        "https://www.331-rent.com/",
    ),
    AdCreative(
        "cbt-inline",
        "inline",
        "CBT4.jpg",
        "CBT Real Estate Services",
        "CBT Real Estate Services",
        "https://www.facebook.com/CBTRealEstateServices/",
    ),
    AdCreative(
        "plains-bank-inline",
        "inline",
        "PlainsBank250.jpg",
        "Plains Bank",
        "Plains Bank",
        PARTNER_DIRECTORY_PATH,
    ),
    AdCreative(
        "patriot-dispatch-inline",
        "inline",
        "PatriotMessaging.jpg",
        "Patriot Dispatch",
        "Patriot Dispatch",
        "https://patriotsforaction.org/messaging",
    ),
    AdCreative(
        "patriot-dispatch-card-inline",
        "inline",
        "PatriotDispatch.jpg",
        "Patriot Dispatch",
        "Patriot Dispatch",
        "https://patriotsforaction.org/messaging",
    ),
    AdCreative(
        "pasture-exchange-inline",
        "inline",
        "PastureEXCHANGELogo.jpg",
        "Pasture Exchange",
        "Pasture Exchange",
        PARTNER_DIRECTORY_PATH,
    ),
    AdCreative(
        "patriot-trailer-inline",
        "inline",
        "PatriotTrailerStore.jpg",
        "Patriot Trailer Store",
        "Patriot Trailer Store",
        "https://piaevents.com/",
    ),
    AdCreative(
        "guerrilla-gear-inline",
        "inline",
        "ad-guerilla-gear.png",
        "Guerrilla Gear",
        "Guerrilla Gear",
        "https://www.guerrillagear.com/",
    ),
    AdCreative(
        "amberwood-brush-inline",
        "inline",
        "Amberwood-Brush-Site-250.jpg",
        "Amberwood Brush",
        "Amberwood Brush",
        PARTNER_DIRECTORY_PATH,
    ),
    AdCreative("arw-inline", "inline", "ARWLogo250.jpg", "ARW", "ARW", PARTNER_DIRECTORY_PATH),
    AdCreative(
        "brown-gmc-inline",
        "inline",
        "BrownGMC-250.jpg",
        "Brown GMC",
        "Brown GMC",
        PARTNER_DIRECTORY_PATH,
    ),
    AdCreative(
        "canyon-ridge-inline",
        "inline",
        "CanyonRidge250.jpg",
        "Canyon Ridge",
        "Canyon Ridge",
        PARTNER_DIRECTORY_PATH,
    ),
    AdCreative(
        "catchings-inline",
        "inline",
        "Catchings250.jpg",
        "Catchings",
        "Catchings",
        PARTNER_DIRECTORY_PATH,
    ),
    AdCreative(
        "dyers-inline",
        "inline",
        "Dyers250.jpg",
        "Dyer's Bar-B-Que",
        "Dyer's Bar-B-Que",
        PARTNER_DIRECTORY_PATH,
    ),
    AdCreative(
        "hoffbrau-inline",
        "inline",
        "Hoffbrau250.jpg",
        "Hoffbrau",
        "Hoffbrau",
        PARTNER_DIRECTORY_PATH,
    ),
    AdCreative(
        "become-a-patriot-inline",
        "inline",
        "BecomeAPatriot.jpg",
        "Become a Patriot",
        "Become a Patriot",
        "https://community.patriotsinaction.com/",
    ),
    AdCreative(
        "become-a-patriot-2-inline",
        "inline",
        "BecomeAPatriot2.jpg",
        "Become a Patriot",
        "Become a Patriot",
        "https://community.patriotsinaction.com/",
    ),
    AdCreative(
        "lawyers-title-inline",
        "inline",
        "LawyersTitle250.jpg",
        "Lawyers Title",
        "Lawyers Title",
        PARTNER_DIRECTORY_PATH,
    ),
    AdCreative(
        "merch-inline",
        "inline",
        "PIAStore.jpg",
        "The Patriot Merch Store",
        "The Patriot Merch Store",
        "https://shop.patriotsinaction.com/",
    ),
    AdCreative(
        "pestcon-inline", "inline", "PestCon250.jpg", "PestCon", "PestCon", PARTNER_DIRECTORY_PATH
    ),
    AdCreative(
        "lemc-banner",
        "banner",
        "LEMC980.jpg",
        "LEMC Realty",
        "LEMC Realty",
        "https://www.331-rent.com/",
    ),
    AdCreative(
        "mattress-banner",
        "banner",
        "matress-ad.jpg",
        "Mattress By Appointment",
        "Mattress By Appointment",
        PARTNER_DIRECTORY_PATH,
    ),
    AdCreative(
        "pasture-exchange-banner",
        "banner",
        "Pasture-Exchange980.jpg",
        "Pasture Exchange",
        "Pasture Exchange",
        PARTNER_DIRECTORY_PATH,
    ),
    AdCreative(
        "pia-banner",
        "banner",
        "PIA980.jpg",
        "Patriots in Action",
        "Patriots in Action",
        "https://community.patriotsinaction.com/",
    ),
)
