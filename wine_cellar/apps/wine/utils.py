import os

from django.conf import settings
from PIL import Image


def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return "user_{0}/{1}".format(instance.user.pk, filename)


def make_thumbnail(instance, height=225):
    """
    Creates a proportional thumbnail with given height.
    Returns the path to the thumbnail file.
    """
    image_path = instance.image.name
    full_path = os.path.join(settings.MEDIA_ROOT, image_path)
    img = Image.open(full_path)

    aspect = img.width / img.height
    width = int(height * aspect)

    img.thumbnail((width, height), Image.LANCZOS)
    base, ext = os.path.splitext(image_path)
    name = f"{base}_thumb{ext}"
    thumb_full_path = os.path.join(settings.MEDIA_ROOT, name)

    img.save(thumb_full_path, format=img.format, quality=100)
    return name
