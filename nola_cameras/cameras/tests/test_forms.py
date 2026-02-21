from django.test import TestCase

from cameras.forms import CameraReportForm
from cameras.models import Camera

VALID_DATA = {
    "cross_road": "Bourbon St & St Peter St",
    "latitude": "29.9585",
    "longitude": "-90.0644",
    "website": "",  # honeypot must be empty
}


class CameraReportFormTests(TestCase):
    def test_valid_form_saves_pending_camera(self):
        form = CameraReportForm(data=VALID_DATA)
        self.assertTrue(form.is_valid(), form.errors)
        camera = form.save()
        self.assertEqual(camera.status, Camera.Status.PENDING)
        self.assertIsNotNone(camera.pk)

    def test_honeypot_filled_is_invalid(self):
        data = {**VALID_DATA, "website": "http://spam.com"}
        form = CameraReportForm(data=data)
        self.assertFalse(form.is_valid())

    def test_missing_cross_road_is_invalid(self):
        data = {**VALID_DATA, "cross_road": ""}
        form = CameraReportForm(data=data)
        self.assertFalse(form.is_valid())

    def test_latitude_out_of_range(self):
        data = {**VALID_DATA, "latitude": "999"}
        form = CameraReportForm(data=data)
        self.assertFalse(form.is_valid())

    def test_longitude_out_of_range(self):
        data = {**VALID_DATA, "longitude": "999"}
        form = CameraReportForm(data=data)
        self.assertFalse(form.is_valid())

    def test_form_creates_point_geometry(self):
        form = CameraReportForm(data=VALID_DATA)
        self.assertTrue(form.is_valid(), form.errors)
        camera = form.save()
        self.assertAlmostEqual(camera.location.y, 29.9585, places=4)
        self.assertAlmostEqual(camera.location.x, -90.0644, places=4)
