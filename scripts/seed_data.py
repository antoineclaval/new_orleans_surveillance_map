"""
Seed script for New Orleans Camera Mapping.
Creates sample camera data for development and testing.

Run with: python manage.py shell < scripts/seed_data.py
"""

from django.contrib.gis.geos import Point
from cameras.models import Camera

# Sample camera data for New Orleans
# Coordinates are (longitude, latitude) for PostGIS Point
SAMPLE_CAMERAS = [
    {
        "cross_road": "Canal St & Bourbon St",
        "street_address": "100 Canal St",
        "location": Point(-90.0686, 29.9527, srid=4326),
        "facial_recognition": True,
        "associated_shop": "",
        "status": Camera.Status.VETTED,
        "reported_by": "seed_data",
    },
    {
        "cross_road": "Frenchmen St & Chartres St",
        "street_address": "",
        "location": Point(-90.0583, 29.9642, srid=4326),
        "facial_recognition": False,
        "associated_shop": "The Spotted Cat Music Club",
        "status": Camera.Status.VETTED,
        "reported_by": "seed_data",
    },
    {
        "cross_road": "Magazine St & Napoleon Ave",
        "street_address": "3100 Magazine St",
        "location": Point(-90.0925, 29.9267, srid=4326),
        "facial_recognition": False,
        "associated_shop": "",
        "status": Camera.Status.VETTED,
        "reported_by": "seed_data",
    },
    {
        "cross_road": "St Charles Ave & Lee Circle",
        "street_address": "",
        "location": Point(-90.0780, 29.9430, srid=4326),
        "facial_recognition": True,
        "associated_shop": "",
        "status": Camera.Status.VETTED,
        "reported_by": "seed_data",
    },
    {
        "cross_road": "Decatur St & Jackson Square",
        "street_address": "500 Decatur St",
        "location": Point(-90.0630, 29.9575, srid=4326),
        "facial_recognition": True,
        "associated_shop": "",
        "status": Camera.Status.VETTED,
        "reported_by": "seed_data",
    },
    {
        "cross_road": "Tchoupitoulas St & Julia St",
        "street_address": "",
        "location": Point(-90.0673, 29.9440, srid=4326),
        "facial_recognition": False,
        "associated_shop": "Warehouse District Gallery",
        "status": Camera.Status.VETTED,
        "reported_by": "seed_data",
    },
    {
        "cross_road": "Esplanade Ave & N Rampart St",
        "street_address": "",
        "location": Point(-90.0612, 29.9625, srid=4326),
        "facial_recognition": False,
        "associated_shop": "",
        "status": Camera.Status.VETTED,
        "reported_by": "seed_data",
    },
    {
        "cross_road": "Poydras St & Loyola Ave",
        "street_address": "1000 Poydras St",
        "location": Point(-90.0742, 29.9495, srid=4326),
        "facial_recognition": True,
        "associated_shop": "",
        "status": Camera.Status.VETTED,
        "reported_by": "seed_data",
    },
    {
        "cross_road": "Claiborne Ave & Martin Luther King Blvd",
        "street_address": "",
        "location": Point(-90.0850, 29.9625, srid=4326),
        "facial_recognition": False,
        "associated_shop": "",
        "status": Camera.Status.VETTED,
        "reported_by": "seed_data",
    },
    {
        "cross_road": "Carrollton Ave & Oak St",
        "street_address": "8200 Oak St",
        "location": Point(-90.1270, 29.9345, srid=4326),
        "facial_recognition": False,
        "associated_shop": "Oak Street Coffee",
        "status": Camera.Status.VETTED,
        "reported_by": "seed_data",
    },
    # Pending cameras (for testing admin review)
    {
        "cross_road": "Royal St & Toulouse St",
        "street_address": "",
        "location": Point(-90.0656, 29.9578, srid=4326),
        "facial_recognition": False,
        "associated_shop": "Antique Shop",
        "status": Camera.Status.PENDING,
        "reported_by": "test_user@example.com",
    },
    {
        "cross_road": "Dauphine St & Ursulines Ave",
        "street_address": "1300 Dauphine St",
        "location": Point(-90.0614, 29.9608, srid=4326),
        "facial_recognition": True,
        "associated_shop": "",
        "status": Camera.Status.PENDING,
        "reported_by": "anonymous",
    },
    # Rejected camera (for testing)
    {
        "cross_road": "Test Location - Invalid",
        "street_address": "123 Fake St",
        "location": Point(-90.0700, 29.9500, srid=4326),
        "facial_recognition": False,
        "associated_shop": "",
        "status": Camera.Status.REJECTED,
        "reported_by": "spam@example.com",
        "notes": "Rejected - location could not be verified",
    },
]


def seed_cameras():
    """Create sample cameras in the database."""
    created = 0
    skipped = 0

    for camera_data in SAMPLE_CAMERAS:
        # Check if camera already exists at this location
        existing = Camera.objects.filter(
            cross_road=camera_data["cross_road"]
        ).exists()

        if not existing:
            Camera.objects.create(**camera_data)
            created += 1
            print(f"Created: {camera_data['cross_road']}")
        else:
            skipped += 1
            print(f"Skipped (exists): {camera_data['cross_road']}")

    print(f"\nSeed complete: {created} created, {skipped} skipped")
    print(f"Total cameras in database: {Camera.objects.count()}")
    print(f"  - Vetted: {Camera.objects.filter(status='vetted').count()}")
    print(f"  - Pending: {Camera.objects.filter(status='pending').count()}")
    print(f"  - Rejected: {Camera.objects.filter(status='rejected').count()}")


if __name__ == "__main__":
    seed_cameras()
else:
    # When run via shell < script.py
    seed_cameras()
