from django.core.management.base import BaseCommand
from chat.models import Room, Client
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = "Seed the database"

    def handle(self, *args, **options):
        Room.objects.get_or_create(name="ellios")
        for room in Room.objects.all():
            room.occupants.clear()
        User.objects.all().delete()
