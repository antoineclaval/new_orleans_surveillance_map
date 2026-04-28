from django.test import TestCase

from cameras.serializers import CameraGeoSerializer

from .utils import make_camera


class CameraGeoSerializerTests(TestCase):
    def setUp(self):
        self.camera = make_camera()

    def test_geo_serializer_fields(self):
        data = CameraGeoSerializer(self.camera).data
        props = data["properties"]
        self.assertIn("photos", props)
        self.assertIsInstance(props["photos"], list)

    def test_geo_serializer_geojson_shape(self):
        data = CameraGeoSerializer(self.camera).data
        self.assertEqual(data["type"], "Feature")
        self.assertEqual(data["geometry"]["type"], "Point")
        self.assertIsInstance(data["properties"], dict)
