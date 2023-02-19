from django.db import models
from django.contrib.auth.models import User


# Create your models here.
class Room(models.Model):
    name = models.CharField(max_length=255)
    occupants = models.ManyToManyField(User)

    def is_full(self):
        return self.occupants.count() >= 2
