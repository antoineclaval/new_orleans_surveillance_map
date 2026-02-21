from django.test import TestCase

from cameras.serializers import CameraDetailSerializer, CameraGeoSerializer

from .utils import make_camera


class CameraGeoSerializerTests(TestCase):
    def setUp(self):
        self.camera = make_camera()

    def test_geo_serializer_fields(self):
        data = CameraGeoSerializer(self.camera).data
        props = data["properties"]
        self.assertIn("image", props)
        self.assertIn("image_2", props)
        self.assertIn("image_3", props)

    def test_geo_serializer_geojson_shape(self):
        data = CameraGeoSerializer(self.camera).data
        self.assertEqual(data["type"], "Feature")
        self.assertEqual(data["geometry"]["type"], "Point")
        self.assertIsInstance(data["properties"], dict)


class CameraDetailSerializerTests(TestCase):
    def setUp(self):
        self.camera = make_camera()

    def test_detail_serializer_lat_lng(self):
        data = CameraDetailSerializer(self.camera).data
        self.assertIn("latitude", data)
        self.assertIn("longitude", data)
        self.assertAlmostEqual(data["latitude"], self.camera.latitude, places=4)
        self.assertAlmostEqual(data["longitude"], self.camera.longitude, places=4)
