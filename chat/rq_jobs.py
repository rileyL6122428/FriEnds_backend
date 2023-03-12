from django_rq import job, get_scheduler, get_queue
from chat.models import Client
from datetime import timedelta
from django.utils import timezone


@job
def delete_unuathenticated_clients():
    Client.objects.filter(
        user__isnull=True,
        connection_time__lte=timezone.now() - timedelta(minutes=1),
    ).delete()
