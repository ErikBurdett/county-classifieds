from __future__ import annotations

from uuid import UUID

from .models import AccountStatus, SellerProfile, SellerProfileRevision


def public_seller_profile(*, public_id: UUID) -> SellerProfile | None:
    """Return an active seller profile without loading private account fields."""
    return (
        SellerProfile.objects.select_related("current_approved_revision")
        .filter(
            public_id=public_id,
            user__account_status=AccountStatus.ACTIVE,
            user__is_active=True,
        )
        .first()
    )


def get_current_public_seller_profile_revision(*, public_id: UUID) -> SellerProfileRevision | None:
    """Return only the approved revision currently selected for a public profile."""
    profile = public_seller_profile(public_id=public_id)
    return profile.current_approved_revision if profile is not None else None
