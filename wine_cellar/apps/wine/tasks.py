from datetime import timedelta

from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone

from wine_cellar.apps.wine.emails import (
    send_drink_by_reminder,
    send_opened_bottle_reminder,
)
from wine_cellar.apps.wine.models import Vintage


@shared_task(name="drink_by_reminder")
def drink_by_reminder():
    User = get_user_model()
    users = (
        User.objects.exclude(email__isnull=True)
        .exclude(email__exact="")
        .exclude(user_settings__notifications=False)
    )
    date = timezone.now().date() + timedelta(days=14)
    for user in users:
        vintages = Vintage.objects.filter(
            wine__user=user, drink_by=date, storageitem__isnull=False
        ).distinct()
        if vintages.count() > 0:
            send_drink_by_reminder(user, vintages)


@shared_task(name="opened_bottle_reminder")
def opened_bottle_reminder():
    from wine_cellar.apps.storage.models import StorageItem

    User = get_user_model()
    users = (
        User.objects.exclude(email__isnull=True)
        .exclude(email__exact="")
        .exclude(user_settings__notifications=False)
    )
    today = timezone.now().date()
    for user in users:
        items = StorageItem.objects.filter(
            user=user, opened=True, deleted=False, drink_by=today
        )
        if items.exists():
            send_opened_bottle_reminder(user, items)
