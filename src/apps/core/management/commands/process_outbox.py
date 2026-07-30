from __future__ import annotations

import os
import socket
from argparse import ArgumentParser
from typing import Any

from django.core.management.base import BaseCommand

from apps.core.outbox import process_batch


class Command(BaseCommand):
    help = "Claim and process a bounded batch of durable outbox events."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--batch-size", type=int, default=25)
        parser.add_argument("--batches", type=int, default=1)

    def handle(self, *_args: object, **options: Any) -> None:
        batch_size = int(options["batch_size"])
        batches = int(options["batches"])
        if batch_size < 1 or batches < 1:
            self.stderr.write("batch-size and batches must be positive.")
            return
        worker_id = f"{socket.gethostname()}-{os.getpid()}"[:64]
        totals = {"claimed": 0, "processed": 0, "retry": 0, "failed": 0, "skipped": 0}
        for _ in range(batches):
            counts = process_batch(worker_id=worker_id, batch_size=batch_size)
            for key, value in counts.items():
                totals[key] += value
            if counts["claimed"] == 0:
                break
        self.stdout.write("outbox " + " ".join(f"{key}={value}" for key, value in totals.items()))
