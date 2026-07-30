from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import User
from apps.core.demo_credentials import record_local_demo_credential

DEMO_STAFF_EMAIL = "admin@local.test"
DEMO_STAFF_PASSWORD = "LocalStaffOnly-ChangeMe-2026!"  # noqa: S105 - DEBUG-only fixture


class Command(BaseCommand):
    help = "Create the local management-console superuser; DEBUG only."

    @transaction.atomic
    def handle(self, *_args: object, **_options: object) -> None:
        if not settings.DEBUG:
            raise CommandError("seed_demo_staff may only run with DEBUG enabled.")

        user, created = User.objects.get_or_create(
            email=DEMO_STAFF_EMAIL,
            defaults={
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            },
        )
        if created:
            user.set_password(DEMO_STAFF_PASSWORD)
            user.save(update_fields=("password",))
            record_local_demo_credential(email=DEMO_STAFF_EMAIL, password=DEMO_STAFF_PASSWORD)
            self.stdout.write(self.style.SUCCESS("Local demo staff account created."))
        else:
            self.stdout.write("Local demo staff account already exists; it was not changed.")
