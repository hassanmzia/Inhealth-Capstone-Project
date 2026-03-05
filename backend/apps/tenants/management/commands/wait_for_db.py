import time

from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError


class Command(BaseCommand):
    help = "Wait for the database to become available."

    def add_arguments(self, parser):
        parser.add_argument(
            "--timeout",
            type=int,
            default=60,
            help="Seconds to wait before giving up (default: 60).",
        )
        parser.add_argument(
            "--interval",
            type=float,
            default=2.0,
            help="Seconds between retries (default: 2).",
        )

    def handle(self, *args, **options):
        timeout = options["timeout"]
        interval = options["interval"]
        deadline = time.monotonic() + timeout

        self.stdout.write("Waiting for database...")
        while True:
            try:
                conn = connections["default"]
                conn.ensure_connection()
                self.stdout.write(self.style.SUCCESS("Database available."))
                return
            except OperationalError as exc:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise SystemExit(f"Database unavailable after {timeout}s: {exc}") from exc
                self.stdout.write(f"  Database unavailable ({exc}). Retrying in {interval}s...")
                time.sleep(interval)
