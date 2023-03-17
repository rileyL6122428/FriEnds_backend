from django_rq import job, get_scheduler, get_queue
from chat.models import Client
from datetime import timedelta
from django.utils import timezone


@job
def delete_unuathenticated_clients():
    Client.objects.filter(
        user=None,
        last_authed_message_time=None,
        connection_time__lte=timezone.now() - timedelta(minutes=1),
    ).delete()

    auth_clients = Client.objects.filter(
        disconnected=True,
        last_authed_message_time__isnull=False,
        last_authed_message_time__lte=timezone.now() - timedelta(minutes=1),
    ).prefetch_related("user")

    for client in auth_clients:
        client.user.client.delete()
        client.user.delete()
