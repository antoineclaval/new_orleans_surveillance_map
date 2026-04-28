import tempfile

from django.test import TestCase, override_settings

from cameras.forms import CameraReportForm, PhotoProposalForm
from cameras.models import Camera, CameraImage

from .utils import make_camera, make_image_file

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


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class PhotoProposalFormTests(TestCase):
    def setUp(self):
        self.camera = make_camera()

    def test_valid_form_is_valid(self):
        form = PhotoProposalForm(
            data={"photo_type": CameraImage.PhotoType.CLOSE_UP, "proposed_by": "", "website": ""},
            files={"image": make_image_file()},
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_honeypot_filled_is_invalid(self):
        form = PhotoProposalForm(
            data={"photo_type": CameraImage.PhotoType.CLOSE_UP, "proposed_by": "", "website": "spam"},
            files={"image": make_image_file()},
        )
        self.assertFalse(form.is_valid())

    def test_missing_image_is_invalid(self):
        form = PhotoProposalForm(
            data={"photo_type": CameraImage.PhotoType.CLOSE_UP, "proposed_by": "", "website": ""},
        )
        self.assertFalse(form.is_valid())

    def test_save_creates_pending_image_for_camera(self):
        form = PhotoProposalForm(
            data={"photo_type": CameraImage.PhotoType.SURROUNDING, "proposed_by": "tester@example.com", "website": ""},
            files={"image": make_image_file()},
        )
        self.assertTrue(form.is_valid(), form.errors)
        img = form.save(camera=self.camera)
        self.assertEqual(img.status, CameraImage.Status.PENDING)
        self.assertEqual(img.camera, self.camera)
        self.assertEqual(img.photo_type, CameraImage.PhotoType.SURROUNDING)
        self.assertEqual(img.proposed_by, "tester@example.com")
