from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.policies.models import PolicyDocument, PolicyDocumentKind, PolicyDocumentStatus


class Command(BaseCommand):
    help = "Seed non-binding, project-owner draft policy document placeholders (DEBUG only)."

    def handle(self, *_args: object, **_options: object) -> None:
        if not settings.DEBUG:
            raise CommandError("Draft policy seeding is available only with DEBUG=True.")
        for kind, label in PolicyDocumentKind.choices:
            PolicyDocument.objects.get_or_create(
                kind=kind,
                version=1,
                defaults={
                    "title": f"{label} — project-owner draft",
                    "body": (
                        "DRAFT FOR PROJECT-OWNER REVIEW ONLY. This is not legal advice, "
                        "not approved legal language, and not binding production terms. "
                        "Replace with reviewed content before any activation."
                    ),
                    "status": PolicyDocumentStatus.DRAFT,
                },
            )
        self.stdout.write(self.style.SUCCESS("Draft policy document placeholders are available."))
