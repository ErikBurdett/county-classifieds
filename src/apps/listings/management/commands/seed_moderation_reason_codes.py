from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.listings.models import ModerationReasonCode

REASON_CODES = (
    ("prohibited_weapons", "Prohibited content", "Weapons and firearms are not allowed.", True),
    (
        "prohibited_controlled_substances",
        "Prohibited content",
        "Controlled substances are not allowed.",
        True,
    ),
    ("prohibited_adult_services", "Prohibited content", "Adult services are not allowed.", True),
    (
        "prohibited_financial_crypto",
        "Prohibited content",
        "Financial and crypto offers are not allowed.",
        True,
    ),
    (
        "prohibited_scams",
        "Safety",
        "This listing appears to involve a scam or unsafe payment request.",
        True,
    ),
    (
        "prohibited_stolen_counterfeit",
        "Prohibited content",
        "Stolen or counterfeit goods are not allowed.",
        True,
    ),
    ("prohibited_trafficking", "Safety", "This listing requires staff safety review.", True),
    (
        "incomplete_listing",
        "Listing quality",
        "Please complete the required listing information.",
        False,
    ),
    (
        "wrong_category",
        "Listing quality",
        "Please choose the category that best matches your listing.",
        False,
    ),
)


class Command(BaseCommand):
    help = "Seed baseline version 1 moderation reason codes for local development."

    def handle(self, *_args: object, **_options: object) -> None:
        if not settings.DEBUG:
            raise CommandError("This local-development seed command requires DEBUG=True.")
        created = 0
        for code, category, seller_text, escalation in REASON_CODES:
            _reason, was_created = ModerationReasonCode.objects.update_or_create(
                code=code,
                defaults={
                    "category": category,
                    "seller_facing_text": seller_text,
                    "requires_escalation": escalation,
                    "is_active": True,
                    "version": 1,
                },
            )
            created += int(was_created)
        self.stdout.write(self.style.SUCCESS(f"Moderation reason codes ready; created {created}."))
