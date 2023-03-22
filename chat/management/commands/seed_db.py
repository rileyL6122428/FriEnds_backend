from django.core.management.base import BaseCommand
from chat.models import Room, Client, Game
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = "Seed the database"

    def handle(self, *args, **options):
        User.objects.all().delete()
        Room.objects.all().delete()
        Game.objects.all().delete()

        ellios_room, created = Room.objects.get_or_create(name="ellios")
        for room in Room.objects.all():
            room.occupants.clear()
        Game.create(ellios_room)
