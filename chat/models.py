from django.db import models
from django.contrib.auth.models import User


# Create your models here.
class Room(models.Model):
    name = models.CharField(max_length=255)
    # occupants = models.ForeignKey(
    #     User,
    #     on_delete=models.PROTECT,
    #     blank=True,
    #     null=True,
    # )
    occupants = models.ManyToManyField(User)
