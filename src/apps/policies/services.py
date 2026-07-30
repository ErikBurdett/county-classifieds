from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.accounts.models import User
from apps.listings.models import Listing

from .models import PolicyAcceptance, PolicyDocument, PolicyDocumentStatus


def active_listing_documents() -> list[PolicyDocument]:
    return list(
        PolicyDocument.objects.filter(
            status=PolicyDocumentStatus.ACTIVE, requires_listing_acceptance=True
        ).order_by("kind", "-version")
    )


@transaction.atomic
def accept_current_listing_policies(*, user: User, listing: Listing) -> list[PolicyAcceptance]:
    """Capture the exact active versions for one seller-owned listing."""
    acceptances: list[PolicyAcceptance] = []
    for document in active_listing_documents():
        acceptance, _created = PolicyAcceptance.objects.get_or_create(
            document=document, user=user, listing=listing
        )
        acceptances.append(acceptance)
    return acceptances


def require_current_listing_acceptances(*, user: User, listing: Listing) -> None:
    documents = active_listing_documents()
    if not documents:
        return
    accepted_ids = set(
        PolicyAcceptance.objects.filter(
            user=user, listing=listing, document__in=documents
        ).values_list("document_id", flat=True)
    )
    missing = [
        document.get_kind_display() for document in documents if document.id not in accepted_ids
    ]
    if missing:
        raise ValidationError(
            "Accept the current policy version(s) before submitting: " + ", ".join(missing) + "."
        )
