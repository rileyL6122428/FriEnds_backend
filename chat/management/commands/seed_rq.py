from django.core.management.base import BaseCommand

from django_rq import get_scheduler, get_queue
from django.utils import timezone
from chat.rq_jobs import clean_up_clients


class Command(BaseCommand):
    help = "Seed the database"

    def handle(self, *args, **options):
        queue = get_queue("default")
        queue.empty()

        scheduler = get_scheduler("default")

        scheduler.schedule(
            scheduled_time=timezone.now(),
            func=clean_up_clients,
            interval=60,
        )
