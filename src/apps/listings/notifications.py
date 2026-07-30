from __future__ import annotations

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from apps.core.models import OutboxEvent

from .models import Listing

SUBJECTS = {
    "listing.approved": "Your listing has been approved",
    "listing.changes_requested": "Changes are requested for your listing",
    "listing.rejected": "Your listing was not approved",
    "listing.sold": "Your listing is marked sold",
    "listing.expired": "Your listing has expired",
    "listing.expiration_reminder": "Your listing expires soon",
}


def handle_listing_notification(event: OutboxEvent) -> None:
    """Send one owner email using only the event's safe, minimal payload."""
    listing = Listing.objects.select_related("seller__user").get(pk=event.payload["listing_id"])
    subject = SUBJECTS[event.event_type]
    context = {
        "listing_title": listing.title,
        "expires_at": listing.expires_at,
        "event_type": event.event_type,
        "seller_message": event.payload.get("seller_message", ""),
        "days_remaining": event.payload.get("days_remaining"),
        "sent_at": timezone.now(),
    }
    text_body = render_to_string("core/email/listing_notification.txt", context)
    html_body = render_to_string("core/email/listing_notification.html", context)
    message = EmailMultiAlternatives(
        subject=subject, body=text_body, to=[listing.seller.user.email]
    )
    message.attach_alternative(html_body, "text/html")
    message.send(fail_silently=False)
