from django.test import TestCase
from rest_framework.test import APIClient

from cameras.models import Camera

from .utils import make_camera


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

    def test_list_includes_image_fields(self):
        make_camera()
        response = self.client.get("/api/cameras/")
        self.assertEqual(response.data["type"], "FeatureCollection")
        props = response.data["features"][0]["properties"]
        self.assertIn("image", props)
        self.assertIn("image_2", props)
        self.assertIn("image_3", props)


class CameraDetailAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_detail_returns_vetted_camera(self):
        camera = make_camera()
        response = self.client.get(f"/api/cameras/{camera.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["cross_road"], camera.cross_road)

    def test_detail_404_for_pending(self):
        camera = make_camera(status=Camera.Status.PENDING)
        response = self.client.get(f"/api/cameras/{camera.pk}/")
        self.assertEqual(response.status_code, 404)

    def test_detail_includes_lat_lng(self):
        camera = make_camera()
        response = self.client.get(f"/api/cameras/{camera.pk}/")
        self.assertIn("latitude", response.data)
        self.assertIn("longitude", response.data)
        self.assertAlmostEqual(response.data["latitude"], camera.latitude, places=4)
        self.assertAlmostEqual(response.data["longitude"], camera.longitude, places=4)
