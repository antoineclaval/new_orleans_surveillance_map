from django.contrib.gis.geos import Point

from cameras.models import Camera


def make_camera(**kwargs):
    """Return a saved Camera with sensible defaults."""
    defaults = {
        "cross_road": "Canal St & Royal St",
        "location": Point(-90.0715, 29.9511),  # lon, lat
        "status": Camera.Status.VETTED,
    }
    defaults.update(kwargs)
    return Camera.objects.create(**defaults)
