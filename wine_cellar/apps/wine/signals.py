import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from wine_cellar.apps.wine.models import WineImage
from wine_cellar.apps.wine.utils import make_thumbnail

logger = logging.getLogger(__name__)


@receiver(post_save, sender=WineImage)
def generate_thumbnail(sender, instance, **kwargs):
    if instance.image and not instance.thumbnail:
        try:
            thumb_name = make_thumbnail(instance)
        except Exception:
            logger.warning(
                "Failed to generate thumbnail for WineImage %s",
                instance.pk,
                exc_info=True,
            )
            return
        instance.thumbnail.name = thumb_name
        instance.save(update_fields=["thumbnail"])
