from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image


def random_png(filename):
    buf = BytesIO()
    Image.new("RGB", (1, 1)).save(buf, format="PNG")
    return SimpleUploadedFile(filename, buf.getvalue(), content_type="image/png")
