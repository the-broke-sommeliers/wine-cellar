import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wine_cellar.config.settings")

celery_app = Celery()
celery_app.config_from_object("django.conf:settings", namespace="CELERY")
celery_app.autodiscover_tasks()

celery_app.conf.beat_schedule = {
    "drink_by_reminder": {
        "task": "drink_by_reminder",
        "schedule": crontab(minute="30", hour="2"),
    },
}
