from django.test import TestCase
from rest_framework.test import APIClient

from cameras.models import Camera, CameraImage

from .utils import make_camera, make_camera_image


class CameraListAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_list_returns_only_vetted(self):
        make_camera(status=Camera.Status.PENDING, cross_road="Pending Camera")
        make_camera(status=Camera.Status.VETTED, cross_road="Vetted Camera")
        response = self.client.get("/api/cameras/")
        self.assertEqual(response.status_code, 200)
        cross_roads = [f["properties"]["cross_road"] for f in response.data["features"]]
        self.assertIn("Vetted Camera", cross_roads)
        self.assertNotIn("Pending Camera", cross_roads)

    def test_list_is_geojson_feature_collection(self):
        make_camera()
        response = self.client.get("/api/cameras/")
        self.assertEqual(response.data["type"], "FeatureCollection")
        self.assertIsInstance(response.data["features"], list)

    def test_list_filter_facial_recognition(self):
        make_camera(facial_recognition=True, cross_road="FR Camera")
        make_camera(facial_recognition=False, cross_road="Non-FR Camera")
        response = self.client.get("/api/cameras/?facial_recognition=true")
        cross_roads = [f["properties"]["cross_road"] for f in response.data["features"]]
        self.assertIn("FR Camera", cross_roads)
        self.assertNotIn("Non-FR Camera", cross_roads)

    def test_list_filter_has_shop(self):
        make_camera(associated_shop="Corner Store", cross_road="Shop Camera")
        make_camera(cross_road="No Shop Camera")
        response = self.client.get("/api/cameras/?has_shop=true")
        cross_roads = [f["properties"]["cross_road"] for f in response.data["features"]]
        self.assertIn("Shop Camera", cross_roads)
        self.assertNotIn("No Shop Camera", cross_roads)

    def test_list_photos_only_shows_approved(self):
        camera = make_camera()
        make_camera_image(camera, status=CameraImage.Status.APPROVED)
        make_camera_image(camera, status=CameraImage.Status.PENDING)
        make_camera_image(camera, status=CameraImage.Status.REJECTED)
        response = self.client.get("/api/cameras/")
        props = response.data["features"][0]["properties"]
        self.assertIn("photos", props)
        # Only the approved image should appear
        self.assertEqual(len(props["photos"]), 1)
        self.assertIn("url", props["photos"][0])
        self.assertIn("type", props["photos"][0])


