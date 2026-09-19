from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image


def random_png(filename):
    buf = BytesIO()
    Image.new("RGB", (1, 1)).save(buf, format="PNG")
    return SimpleUploadedFile(filename, buf.getvalue(), content_type="image/png")


def exif_jpeg(filename, orientation=6):
    """A real JPEG carrying an EXIF Orientation tag, like a phone camera
    photo - unlike random_png(), this exercises the EXIF-rotation branch of
    make_thumbnail()."""
    buf = BytesIO()
    img = Image.new("RGB", (4, 2), color="red")
    exif = img.getexif()
    exif[0x0112] = orientation  # 0x0112 == 274 == "Orientation"
    img.save(buf, format="JPEG", exif=exif)
    return SimpleUploadedFile(filename, buf.getvalue(), content_type="image/jpeg")


def invalid_image(filename):
    """Non-image bytes wearing an image filename/content-type. Django's
    ImageField.to_python() opens uploads with Pillow, so this should fail
    form validation rather than crash the view."""
    return SimpleUploadedFile(filename, b"not-an-image", content_type="image/png")
