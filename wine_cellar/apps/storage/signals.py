from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver

from wine_cellar.apps.storage.models import Storage


@receiver(post_save, sender=User)
def create_storage(sender, instance, created, **kwargs):
    if created:
        Storage.objects.create(name="Default Shelf", user=instance, description="Default storage for wines", location="Cellar", rows=0, columns=0)