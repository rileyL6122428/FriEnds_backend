from django.core.management.base import BaseCommand
from chat.models import Room


class Command(BaseCommand):
    help = "Seed the database"

    def handle(self, *args, **options):
        Room.objects.get_or_create(name="ellios")
