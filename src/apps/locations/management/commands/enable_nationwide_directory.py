from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.locations.models import County, State


class Command(BaseCommand):
    help = "Enable every imported state and county for the public nationwide directory."

    def handle(self, *_args: Any, **_options: Any) -> None:
        with transaction.atomic():
            states_updated = State.objects.exclude(is_active=True, is_network_enabled=True).update(
                is_active=True, is_network_enabled=True
            )
            counties_updated = County.objects.exclude(
                is_active=True, is_network_enabled=True
            ).update(is_active=True, is_network_enabled=True)

        self.stdout.write(
            self.style.SUCCESS(
                "Enabled nationwide directory: "
                f"{states_updated} states and {counties_updated} counties updated."
            )
        )
