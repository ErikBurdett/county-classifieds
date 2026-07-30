"""Versioned, controlled reference data for the marketplace taxonomy.

This module deliberately describes browse vocabulary only.  A catalog vertical
does not grant seller posting eligibility: that remains gated by an approved
``ListingKind``, product configuration, and typed vertical implementation.
"""

from __future__ import annotations

from dataclasses import dataclass

MARKETPLACE_CATALOG_VERSION = "2026.07.30.1"


@dataclass(frozen=True)
class CategorySeed:
    name: str
    slug: str
    display_order: int
    parent_slug: str | None = None


@dataclass(frozen=True)
class VerticalSeed:
    name: str
    slug: str
    display_order: int
    posting_readiness: str
    categories: tuple[CategorySeed, ...]


def _categories(*groups: tuple[str, str, tuple[tuple[str, str], ...]]) -> tuple[CategorySeed, ...]:
    entries: list[CategorySeed] = []
    for group_order, (name, slug, children) in enumerate(groups, start=1):
        entries.append(CategorySeed(name, slug, group_order * 10))
        entries.extend(
            CategorySeed(child_name, child_slug, group_order * 10 + child_order, slug)
            for child_order, (child_name, child_slug) in enumerate(children, start=1)
        )
    return tuple(entries)


MARKETPLACE_CATALOG: tuple[VerticalSeed, ...] = (
    VerticalSeed(
        "Appliances",
        "appliances",
        10,
        (
            "Private Appliances drafts only; no ListingKind, products, submission, "
            "or public listing flow."
        ),
        _categories(
            (
                "Kitchen Appliances",
                "kitchen-appliances",
                (
                    ("Refrigerators & Freezers", "refrigerators-freezers"),
                    ("Ranges & Ovens", "ranges-ovens"),
                    ("Dishwashers", "dishwashers"),
                ),
            ),
            (
                "Laundry Appliances",
                "laundry-appliances",
                (
                    ("Washers", "washers"),
                    ("Dryers", "dryers"),
                    ("Washer-Dryer Combos", "washer-dryer-combos"),
                ),
            ),
            (
                "Small Appliances",
                "small-appliances",
                (
                    ("Coffee & Espresso", "coffee-espresso"),
                    ("Microwaves", "microwaves"),
                    ("Other Small Appliances", "other-small-appliances"),
                ),
            ),
            ("Other", "other", ()),
        ),
    ),
    VerticalSeed(
        "Autos & Vehicles",
        "autos",
        20,
        "Ready only for the existing Automobile ListingKind, products, and typed draft form.",
        _categories(
            (
                "Cars",
                "cars",
                (
                    ("Classic Cars", "classic-cars"),
                    ("Electric & Hybrid Cars", "electric-hybrid-cars"),
                ),
            ),
            (
                "Trucks",
                "trucks",
                (("Pickup Trucks", "pickup-trucks"), ("Commercial Trucks", "commercial-trucks")),
            ),
            (
                "SUVs",
                "suvs",
                (("Compact SUVs", "compact-suvs"), ("Full-Size SUVs", "full-size-suvs")),
            ),
            ("Vans", "vans", (("Cargo Vans", "cargo-vans"), ("Passenger Vans", "passenger-vans"))),
            (
                "Motorcycles",
                "motorcycles",
                (("ATVs & UTVs", "atvs-utvs"), ("Scooters & Mopeds", "scooters-mopeds")),
            ),
            (
                "Trailers",
                "trailers",
                (
                    ("Utility Trailers", "utility-trailers"),
                    ("RV & Camper Trailers", "rv-camper-trailers"),
                ),
            ),
            (
                "Vehicle Parts & Accessories",
                "vehicle-parts-accessories",
                (
                    ("Auto Parts", "auto-parts"),
                    ("Tires & Wheels", "tires-wheels"),
                    ("Vehicle Tools & Accessories", "vehicle-tools-accessories"),
                ),
            ),
            ("Other Autos", "other-autos", ()),
        ),
    ),
    VerticalSeed(
        "Business & Industrial",
        "business-industrial",
        30,
        "Catalog only; no ListingKind, products, or typed seller form.",
        _categories(
            (
                "Commercial Equipment",
                "commercial-equipment",
                (
                    ("Food Service Equipment", "food-service-equipment"),
                    ("Janitorial Equipment", "janitorial-equipment"),
                    ("Warehouse Equipment", "warehouse-equipment"),
                ),
            ),
            (
                "Office",
                "office",
                (
                    ("Office Furniture", "office-furniture"),
                    ("Printers & Copiers", "printers-copiers"),
                    ("Point of Sale", "point-of-sale"),
                ),
            ),
            (
                "Retail & Restaurant",
                "retail-restaurant",
                (("Display Fixtures", "display-fixtures"), ("Store Fixtures", "store-fixtures")),
            ),
            ("Other", "other", ()),
        ),
    ),
    VerticalSeed(
        "Clothing & Personal",
        "clothing-personal",
        40,
        (
            "Private Home & Garden drafts only; no ListingKind, products, submission, "
            "or public listing flow."
        ),
        _categories(
            (
                "Clothing",
                "clothing",
                (
                    ("Men's Clothing", "mens-clothing"),
                    ("Women's Clothing", "womens-clothing"),
                    ("Workwear", "workwear"),
                ),
            ),
            (
                "Shoes & Accessories",
                "shoes-accessories",
                (
                    ("Shoes", "shoes"),
                    ("Bags & Luggage", "bags-luggage"),
                    ("Jewelry & Watches", "jewelry-watches"),
                ),
            ),
            (
                "Personal Care",
                "personal-care",
                (
                    ("Health & Beauty", "health-beauty"),
                    ("Personal Care Appliances", "personal-care-appliances"),
                ),
            ),
            ("Other", "other", ()),
        ),
    ),
    VerticalSeed(
        "Collectibles & Art",
        "collectibles-art",
        50,
        "Catalog only; no ListingKind, products, or typed seller form.",
        _categories(
            (
                "Art",
                "art",
                (
                    ("Paintings & Prints", "paintings-prints"),
                    ("Sculpture", "sculpture"),
                    ("Craft Supplies", "craft-supplies"),
                ),
            ),
            (
                "Collectibles",
                "collectibles",
                (
                    ("Antiques", "antiques"),
                    ("Coins & Currency", "coins-currency"),
                    ("Memorabilia", "memorabilia"),
                ),
            ),
            (
                "Media",
                "media",
                (("Books & Magazines", "books-magazines"), ("Music & Movies", "music-movies")),
            ),
            ("Other", "other", ()),
        ),
    ),
    VerticalSeed(
        "Community",
        "community",
        60,
        "Catalog only; no ListingKind, products, or typed seller form.",
        _categories(
            (
                "Activities",
                "activities",
                (
                    ("Classes & Workshops", "classes-workshops"),
                    ("Events", "events"),
                    ("Volunteer Opportunities", "volunteer-opportunities"),
                ),
            ),
            (
                "Local Groups",
                "local-groups",
                (("Clubs", "clubs"), ("Neighbors & Interest Groups", "neighbors-interest-groups")),
            ),
            (
                "Lost & Found",
                "lost-found",
                (("Lost Items", "lost-items"), ("Found Items", "found-items")),
            ),
            ("Other", "other", ()),
        ),
    ),
    VerticalSeed(
        "Electronics",
        "electronics",
        70,
        "Catalog only; no ListingKind, products, or typed seller form.",
        _categories(
            (
                "Computers & Tablets",
                "computers-tablets",
                (
                    ("Desktop Computers", "desktop-computers"),
                    ("Laptops", "laptops"),
                    ("Tablets", "tablets"),
                ),
            ),
            (
                "Phones & Wearables",
                "phones-wearables",
                (("Mobile Phones", "mobile-phones"), ("Smartwatches", "smartwatches")),
            ),
            (
                "TV, Audio & Video",
                "tv-audio-video",
                (
                    ("Televisions", "televisions"),
                    ("Audio Equipment", "audio-equipment"),
                    ("Cameras", "cameras"),
                ),
            ),
            ("Other", "other", ()),
        ),
    ),
    VerticalSeed(
        "Farm & Ranch",
        "farm-ranch",
        80,
        (
            "Private typed Agricultural Equipment and Pasture drafts are available; "
            "no ListingKind, products, submission, or public flow."
        ),
        _categories(
            (
                "Farm Equipment",
                "farm-equipment",
                (
                    ("Tractors", "tractors"),
                    ("Harvesting Equipment", "harvesting-equipment"),
                    ("Implements", "implements"),
                ),
            ),
            (
                "Ranch Supplies",
                "ranch-supplies",
                (
                    ("Fencing", "fencing"),
                    ("Feed & Water Equipment", "feed-water-equipment"),
                    ("Tack & Supplies", "tack-supplies"),
                ),
            ),
            (
                "Land & Pasture",
                "land-pasture",
                (("Farm Land", "farm-land"), ("Pasture Lease", "pasture-lease")),
            ),
            ("Other", "other", ()),
        ),
    ),
    VerticalSeed(
        "Home & Garden",
        "home-garden",
        90,
        "Catalog only; no ListingKind, products, or typed seller form.",
        _categories(
            (
                "Furniture",
                "furniture",
                (
                    ("Bedroom Furniture", "bedroom-furniture"),
                    ("Living Room Furniture", "living-room-furniture"),
                    ("Dining Room Furniture", "dining-room-furniture"),
                ),
            ),
            (
                "Home Improvement",
                "home-improvement",
                (
                    ("Building Materials", "building-materials"),
                    ("Lighting", "lighting"),
                    ("Plumbing & Electrical", "plumbing-electrical"),
                ),
            ),
            (
                "Garden & Outdoor Living",
                "garden-outdoor-living",
                (
                    ("Plants & Seeds", "plants-seeds"),
                    ("Patio & Garden Furniture", "patio-garden-furniture"),
                    ("Lawn Care", "lawn-care"),
                ),
            ),
            ("Other", "other", ()),
        ),
    ),
    VerticalSeed(
        "Jobs",
        "jobs",
        100,
        "Catalog only; no ListingKind, products, or typed seller form.",
        _categories(
            (
                "Employment",
                "employment",
                (
                    ("Full-Time Jobs", "full-time-jobs"),
                    ("Part-Time Jobs", "part-time-jobs"),
                    ("Seasonal Jobs", "seasonal-jobs"),
                ),
            ),
            (
                "Industry",
                "industry",
                (
                    ("Construction Jobs", "construction-jobs"),
                    ("Healthcare Jobs", "healthcare-jobs"),
                    ("Office & Professional Jobs", "office-professional-jobs"),
                ),
            ),
            ("Other", "other", ()),
        ),
    ),
    VerticalSeed(
        "Kids & Baby",
        "kids-baby",
        110,
        "Catalog only; no ListingKind, products, or typed seller form.",
        _categories(
            (
                "Baby Gear",
                "baby-gear",
                (
                    ("Strollers", "strollers"),
                    ("Car Seats", "car-seats"),
                    ("Nursery Furniture", "nursery-furniture"),
                ),
            ),
            (
                "Kids Clothing",
                "kids-clothing",
                (("Baby Clothing", "baby-clothing"), ("Kids Clothing", "childrens-clothing")),
            ),
            (
                "Toys & Games",
                "toys-games",
                (("Educational Toys", "educational-toys"), ("Outdoor Toys", "outdoor-toys")),
            ),
            ("Other", "other", ()),
        ),
    ),
    VerticalSeed(
        "Livestock & Animals",
        "livestock-animals",
        120,
        (
            "Private typed Livestock drafts are available; no ListingKind, "
            "products, submission, or public flow. Pets are a catalog group "
            "only, not policy approval."
        ),
        _categories(
            (
                "Livestock",
                "livestock",
                (
                    ("Cattle", "cattle"),
                    ("Goats & Sheep", "goats-sheep"),
                    ("Horses", "horses"),
                    ("Poultry", "poultry"),
                ),
            ),
            (
                "Pets",
                "pets",
                (("Dogs", "dogs"), ("Cats", "cats"), ("Small Animals", "small-animals")),
            ),
            (
                "Animal Supplies",
                "animal-supplies",
                (
                    ("Feed & Bedding", "feed-bedding"),
                    ("Animal Housing", "animal-housing"),
                    ("Pet Supplies", "pet-supplies"),
                ),
            ),
            ("Other", "other", ()),
        ),
    ),
    VerticalSeed(
        "Real Estate",
        "real-estate",
        130,
        (
            "Private typed Home drafts are available; no ListingKind, products, "
            "submission, or public flow."
        ),
        _categories(
            (
                "Homes for Sale",
                "homes-for-sale",
                (
                    ("Single-Family Homes", "single-family-homes"),
                    ("Condominiums & Townhomes", "condos-townhomes"),
                    ("Manufactured Homes", "manufactured-homes"),
                ),
            ),
            (
                "Land",
                "land",
                (
                    ("Residential Land", "residential-land"),
                    ("Commercial Land", "commercial-land"),
                    ("Recreational Land", "recreational-land"),
                ),
            ),
            (
                "Commercial Property",
                "commercial-property",
                (
                    ("Office Space", "office-space"),
                    ("Retail Space", "retail-space"),
                    ("Industrial Property", "industrial-property"),
                ),
            ),
            ("Other", "other", ()),
        ),
    ),
    VerticalSeed(
        "Recreation & Hobbies",
        "recreation-hobbies",
        140,
        "Catalog only; no ListingKind, products, or typed seller form.",
        _categories(
            (
                "Games & Puzzles",
                "games-puzzles",
                (
                    ("Board Games", "board-games"),
                    ("Puzzles", "puzzles"),
                    ("Video Games", "video-games"),
                ),
            ),
            (
                "Musical Instruments",
                "musical-instruments",
                (
                    ("Guitars", "guitars"),
                    ("Keyboards", "keyboards"),
                    ("Band Instruments", "band-instruments"),
                ),
            ),
            (
                "Hobby Equipment",
                "hobby-equipment",
                (("Model Kits", "model-kits"), ("Photography Gear", "photography-gear")),
            ),
            ("Other", "other", ()),
        ),
    ),
    VerticalSeed(
        "Rentals",
        "rentals",
        150,
        (
            "Private typed Rental drafts are available; no ListingKind, products, "
            "submission, or public flow."
        ),
        _categories(
            (
                "Homes for Rent",
                "homes-for-rent",
                (
                    ("Houses for Rent", "houses-for-rent"),
                    ("Apartments", "apartments"),
                    ("Rooms & Shared Housing", "rooms-shared-housing"),
                ),
            ),
            (
                "Commercial Rentals",
                "commercial-rentals",
                (("Office Rentals", "office-rentals"), ("Retail Rentals", "retail-rentals")),
            ),
            (
                "Storage & Parking",
                "storage-parking",
                (("Storage Units", "storage-units"), ("Parking Spaces", "parking-spaces")),
            ),
            ("Other", "other", ()),
        ),
    ),
    VerticalSeed(
        "Services",
        "services",
        160,
        "Catalog only; no ListingKind, products, or typed seller form.",
        _categories(
            (
                "Home Services",
                "home-services",
                (
                    ("Cleaning", "cleaning"),
                    ("Landscaping", "landscaping"),
                    ("Repairs & Maintenance", "repairs-maintenance"),
                ),
            ),
            (
                "Professional Services",
                "professional-services",
                (
                    ("Accounting & Bookkeeping", "accounting-bookkeeping"),
                    ("Design & Creative", "design-creative"),
                    ("Technology Services", "technology-services"),
                ),
            ),
            (
                "Lessons & Care",
                "lessons-care",
                (
                    ("Lessons & Tutoring", "lessons-tutoring"),
                    ("Child Care", "child-care"),
                    ("Elder Care", "elder-care"),
                ),
            ),
            ("Other", "other", ()),
        ),
    ),
    VerticalSeed(
        "Sporting & Outdoor",
        "sporting-outdoor",
        170,
        "Catalog only; no ListingKind, products, or typed seller form.",
        _categories(
            (
                "Athletics",
                "athletics",
                (
                    ("Fitness Equipment", "fitness-equipment"),
                    ("Team Sports", "team-sports"),
                    ("Bicycles", "bicycles"),
                ),
            ),
            (
                "Camping & Hiking",
                "camping-hiking",
                (("Camping Gear", "camping-gear"), ("Hiking Gear", "hiking-gear")),
            ),
            (
                "Water Sports",
                "water-sports",
                (
                    ("Boats & Watercraft", "boats-watercraft"),
                    ("Fishing Equipment", "fishing-equipment"),
                    ("Paddle Sports", "paddle-sports"),
                ),
            ),
            ("Other", "other", ()),
        ),
    ),
    VerticalSeed(
        "Tools & Equipment",
        "tools-equipment",
        180,
        "Catalog only; no ListingKind, products, or typed seller form.",
        _categories(
            (
                "Hand & Power Tools",
                "hand-power-tools",
                (
                    ("Hand Tools", "hand-tools"),
                    ("Power Tools", "power-tools"),
                    ("Tool Storage", "tool-storage"),
                ),
            ),
            (
                "Construction Equipment",
                "construction-equipment",
                (
                    ("Generators", "generators"),
                    ("Compressors", "compressors"),
                    ("Ladders & Scaffolding", "ladders-scaffolding"),
                ),
            ),
            (
                "Yard Equipment",
                "yard-equipment",
                (
                    ("Lawn Mowers", "lawn-mowers"),
                    ("Chainsaws", "chainsaws"),
                    ("Snow Equipment", "snow-equipment"),
                ),
            ),
            ("Other", "other", ()),
        ),
    ),
    VerticalSeed(
        "Others",
        "others",
        190,
        (
            "Ready for generic catalog-profile listings. General is an internal "
            "primary leaf; approved seller tags provide the public classification."
        ),
        (CategorySeed("General", "general", 10),),
    ),
)
