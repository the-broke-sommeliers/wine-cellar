from django.db.models.signals import post_save
from django.dispatch import receiver

from wine_cellar.apps.wine.models import WineImage
from wine_cellar.apps.wine.utils import make_thumbnail


@receiver(post_save, sender=WineImage)
def generate_thumbnail(sender, instance, **kwargs):
    if instance.image and not instance.thumbnail:
        thumb_name = make_thumbnail(instance)
        instance.thumbnail.name = thumb_name
        instance.save(update_fields=["thumbnail"])
