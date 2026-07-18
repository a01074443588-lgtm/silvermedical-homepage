import time

from django.core.management.base import BaseCommand

from staff_notifications.dispatch import process_due_jobs
from staff_notifications.models import NotificationConfiguration


class Command(BaseCommand):
    help = "Process queued staff notification jobs."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")
        parser.add_argument("--batch", type=int, default=20)
        parser.add_argument("--sleep", type=int, default=0)

    def handle(self, *args, **options):
        sleep_seconds = options["sleep"] or NotificationConfiguration.current().worker_poll_seconds
        self.stdout.write("Notification worker started.")
        while True:
            counts = process_due_jobs(limit=options["batch"])
            if any(counts.values()):
                self.stdout.write(
                    "Notification jobs processed: "
                    f"sent={counts['sent']} retry={counts['retry']} "
                    f"cancelled={counts['cancelled']}"
                )
            if options["once"]:
                break
            time.sleep(max(sleep_seconds, 2))
