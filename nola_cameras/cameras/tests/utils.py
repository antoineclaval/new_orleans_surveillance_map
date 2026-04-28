import io

from django.contrib.gis.geos import Point
from django.core.files.uploadedfile import SimpleUploadedFile

from cameras.models import Camera, CameraImage


def make_camera(**kwargs):
    """Return a saved Camera with sensible defaults."""
    defaults = {
        "cross_road": "Canal St & Royal St",
        "location": Point(-90.0715, 29.9511),  # lon, lat
        "status": Camera.Status.VETTED,
    }
    defaults.update(kwargs)
    return Camera.objects.create(**defaults)


def make_image_file(name="test.jpg"):
    """Return a minimal valid JPEG as a SimpleUploadedFile."""
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (1, 1)).save(buf, format="JPEG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/jpeg")


def make_camera_image(camera, **kwargs):
    """Return a saved CameraImage with sensible defaults."""
    defaults = {
        "image": "camera_images/test.jpg",
        "photo_type": CameraImage.PhotoType.CLOSE_UP,
        "status": CameraImage.Status.APPROVED,
    }
    defaults.update(kwargs)
    return CameraImage.objects.create(camera=camera, **defaults)
