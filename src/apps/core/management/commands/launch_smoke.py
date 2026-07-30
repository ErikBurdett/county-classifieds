from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.test import Client

HTTP_OK = 200


def _smoke_host() -> str:
    allowed_hosts = settings.ALLOWED_HOSTS
    if not allowed_hosts:
        raise CommandError("launch_smoke requires a configured ALLOWED_HOSTS value.")

    allowed_host = allowed_hosts[0]
    if allowed_host == "*":
        return "localhost"
    if allowed_host.startswith("."):
        return f"smoke{allowed_host}"
    return allowed_host


class Command(BaseCommand):
    help = (
        "Run reproducible local launch-foundation smoke checks; does not contact external services."
    )

    def handle(self, *_args: object, **_options: object) -> None:
        client = Client()
        host = _smoke_host()
        checks = ("/health/live/", "/health/ready/", "/")
        failures = [
            f"{path} returned {response.status_code}"
            for path in checks
            if (response := client.get(path, HTTP_HOST=host)).status_code != HTTP_OK
        ]
        if failures:
            raise CommandError("; ".join(failures))
        self.stdout.write(
            self.style.SUCCESS(
                "Local health and public-path checks passed. Account, submission, moderation, "
                "billing, and outbox workflows remain covered by automated tests."
            )
        )
