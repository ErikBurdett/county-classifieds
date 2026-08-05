from __future__ import annotations

import uuid

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client
from django.urls import reverse

from apps.accounts.forms import SellerProfileForm
from apps.accounts.models import SellerProfile, SellerProfileRevisionStatus, User
from apps.accounts.selectors import get_current_public_seller_profile_revision
from apps.accounts.services import review_seller_profile_revision, submit_seller_profile_revision

pytestmark = pytest.mark.django_db


def create_profile(*, email: str = "seller@example.com") -> SellerProfile:
    user = User.objects.create_user(email=email, password="test-password")
    return SellerProfile.objects.create(user=user, display_name="Seller")


def test_profile_public_id_is_unique_uuid_and_immutable() -> None:
    first = create_profile()
    second = create_profile(email="other@example.com")

    assert isinstance(first.public_id, uuid.UUID)
    assert first.public_id != second.public_id

    first.refresh_from_db()
    first.public_id = uuid.uuid4()
    with pytest.raises(ValueError, match="immutable"):
        first.save()


def test_seller_profile_submission_updates_attribution_and_creates_pending_revision(
    client: Client,
) -> None:
    profile = create_profile()
    client.force_login(profile.user)

    response = client.post(
        reverse("accounts:seller_profile"),
        {
            "display_name": "Updated seller",
            "phone": "555-0100",
            "bio": "A local seller.",
            "website_url": "https://seller.example/",
            "facebook_url": "",
            "instagram_url": "",
            "x_url": "",
            "linkedin_url": "",
            "youtube_url": "",
        },
    )

    profile.refresh_from_db()
    revision = profile.revisions.get()
    assert response.status_code == 302
    assert response["Location"] == reverse("listings:dashboard")
    assert profile.display_name == "Updated seller"
    assert profile.phone == "555-0100"
    assert revision.status == SellerProfileRevisionStatus.PENDING
    assert revision.bio == "A local seller."
    assert revision.website_url == "https://seller.example/"
    assert profile.current_approved_revision is None


def test_profile_link_fields_require_https() -> None:
    profile = create_profile()
    form = SellerProfileForm(
        instance=profile,
        data={
            "display_name": profile.display_name,
            "phone": "",
            "bio": "",
            "website_url": "http://seller.example/",
            "facebook_url": "",
            "instagram_url": "",
            "x_url": "",
            "linkedin_url": "",
            "youtube_url": "",
        },
    )

    assert not form.is_valid()
    assert "website_url" in form.errors


def test_submission_service_rejects_non_https_links() -> None:
    profile = create_profile()

    with pytest.raises(ValidationError, match="Enter a valid URL"):
        submit_seller_profile_revision(
            user=profile.user,
            display_name=profile.display_name,
            phone="",
            content={"website_url": "http://seller.example/"},
        )


def test_approval_records_review_and_selects_current_public_revision() -> None:
    profile = create_profile()
    revision = profile.revisions.create(bio="Approved profile")
    reviewer = User.objects.create_superuser(email="admin@example.com", password="test-password")

    review_seller_profile_revision(
        revision_id=revision.pk,
        reviewer=reviewer,
        status=SellerProfileRevisionStatus.APPROVED,
        note="Looks good.",
    )

    profile.refresh_from_db()
    revision.refresh_from_db()
    assert revision.status == SellerProfileRevisionStatus.APPROVED
    assert revision.reviewer == reviewer
    assert revision.review_note == "Looks good."
    assert revision.reviewed_at is not None
    assert profile.current_approved_revision == revision
    assert get_current_public_seller_profile_revision(public_id=profile.public_id) == revision


def test_public_profile_uses_only_safe_profile_data(client: Client) -> None:
    profile = create_profile()
    profile.phone = "555-0199"
    profile.save(update_fields=("phone", "updated_at"))
    revision = profile.revisions.create(
        status=SellerProfileRevisionStatus.APPROVED,
        bio="Serving the Panhandle.",
        website_url="https://seller.example/",
    )
    profile.current_approved_revision = revision
    profile.save(update_fields=("current_approved_revision", "updated_at"))

    response = client.get(
        reverse("accounts:public_seller_profile", kwargs={"public_id": profile.public_id})
    )

    assert response.status_code == 200
    assert "Serving the Panhandle." in response.content.decode()
    assert "555-0199" not in response.content.decode()
    assert profile.user.email not in response.content.decode()


def test_rejection_preserves_current_approved_revision() -> None:
    profile = create_profile()
    reviewer = User.objects.create_superuser(email="admin@example.com", password="test-password")
    approved_revision = profile.revisions.create(bio="Approved profile")
    review_seller_profile_revision(
        revision_id=approved_revision.pk,
        reviewer=reviewer,
        status=SellerProfileRevisionStatus.APPROVED,
        note="Approved.",
    )
    rejected_revision = profile.revisions.create(bio="Rejected profile")

    review_seller_profile_revision(
        revision_id=rejected_revision.pk,
        reviewer=reviewer,
        status=SellerProfileRevisionStatus.REJECTED,
        note="Please revise.",
    )

    profile.refresh_from_db()
    rejected_revision.refresh_from_db()
    assert rejected_revision.status == SellerProfileRevisionStatus.REJECTED
    assert rejected_revision.reviewer == reviewer
    assert rejected_revision.reviewed_at is not None
    assert profile.current_approved_revision == approved_revision


def test_review_rejects_unauthorized_and_repeat_attempts() -> None:
    profile = create_profile()
    revision = profile.revisions.create(bio="Profile")
    unauthorized_reviewer = User.objects.create_user(
        email="staffless@example.com", password="test-password"
    )

    with pytest.raises(PermissionDenied):
        review_seller_profile_revision(
            revision_id=revision.pk,
            reviewer=unauthorized_reviewer,
            status=SellerProfileRevisionStatus.APPROVED,
            note="No permission.",
        )

    reviewer = User.objects.create_superuser(email="admin@example.com", password="test-password")
    review_seller_profile_revision(
        revision_id=revision.pk,
        reviewer=reviewer,
        status=SellerProfileRevisionStatus.APPROVED,
        note="Approved.",
    )
    with pytest.raises(ValueError, match="Only pending"):
        review_seller_profile_revision(
            revision_id=revision.pk,
            reviewer=reviewer,
            status=SellerProfileRevisionStatus.REJECTED,
            note="Too late.",
        )
