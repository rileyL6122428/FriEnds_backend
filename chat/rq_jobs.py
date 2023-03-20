from django_rq import job
from chat.models import Client
from datetime import timedelta
from django.utils import timezone


@job
def clean_up_clients():
    delete_unauthenticated_clients()
    delete_disconnected_users()


def delete_unauthenticated_clients():
    Client.objects.filter(
        user=None,
        last_authed_message_time=None,
        connection_time__lte=timezone.now() - timedelta(minutes=1),
    ).delete()


def delete_disconnected_users():
    auth_clients = Client.objects.filter(
        connected=False,
        user__isnull=False,
        last_authed_message_time__isnull=False,
        last_authed_message_time__lte=timezone.now() - timedelta(minutes=1),
    ).prefetch_related("user")

    for client in auth_clients:
        client.user.delete()
