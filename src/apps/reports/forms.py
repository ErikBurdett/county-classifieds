from __future__ import annotations

from django import forms

from .models import ListingReportReason


class PublicListingReportForm(forms.Form):
    reason = forms.ChoiceField(choices=ListingReportReason.choices)
    description = forms.CharField(
        required=False,
        max_length=2000,
        widget=forms.Textarea(attrs={"rows": 5}),
        help_text="Do not include passwords, payment details, or other sensitive information.",
    )
    email = forms.EmailField(
        required=False,
        label="Email address (optional)",
        help_text="Only provide this if staff may contact you about the report.",
    )


class TriageListingReportForm(forms.Form):
    action = forms.ChoiceField(
        choices=(
            ("acknowledge", "Acknowledge"),
            ("resolve", "Resolve"),
            ("dismiss", "Dismiss"),
            ("escalate", "Escalate"),
        )
    )
    internal_note = forms.CharField(
        required=False, max_length=2000, widget=forms.Textarea(attrs={"rows": 3})
    )
