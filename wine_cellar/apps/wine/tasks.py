from datetime import timedelta

from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone

from wine_cellar.apps.wine.emails import send_drink_by_reminder
from wine_cellar.apps.wine.models import Wine


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
        wines = Wine.objects.filter(user=user, drink_by=date, stock__gt=0)
        if wines.count() > 0:
            send_drink_by_reminder(user, wines)
