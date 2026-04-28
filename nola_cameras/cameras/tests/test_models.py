from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.test import TestCase

from cameras.models import Camera, CameraImage

from .utils import make_camera, make_camera_image


class CameraDefaultStatusTest(TestCase):
    def test_default_status_is_pending(self):
        camera = Camera.objects.create(
            cross_road="Test St & Canal St",
            location=Point(-90.0715, 29.9511),
        )
        self.assertEqual(camera.status, Camera.Status.PENDING)


class CameraPropertyTests(TestCase):
    def setUp(self):
        self.camera = make_camera()

    def test_latitude_longitude_properties(self):
        self.assertAlmostEqual(self.camera.latitude, 29.9511, places=4)
        self.assertAlmostEqual(self.camera.longitude, -90.0715, places=4)

    def test_str_representation(self):
        self.assertIn(self.camera.cross_road, str(self.camera))


class CameraApproveRejectTests(TestCase):
    def setUp(self):
        self.camera = make_camera(status=Camera.Status.PENDING)
        self.user = User.objects.create_user(username="reviewer", password="pass")

    def test_approve_sets_status_and_timestamps(self):
        self.camera.approve(self.user)
        self.camera.refresh_from_db()
        self.assertEqual(self.camera.status, Camera.Status.VETTED)
        self.assertEqual(self.camera.vetted_by, self.user)
        self.assertIsNotNone(self.camera.vetted_at)

    def test_reject_sets_status_and_timestamps(self):
        self.camera.reject(self.user)
        self.camera.refresh_from_db()
        self.assertEqual(self.camera.status, Camera.Status.REJECTED)
        self.assertEqual(self.camera.vetted_by, self.user)
        self.assertIsNotNone(self.camera.vetted_at)


class CameraImageTests(TestCase):
    def setUp(self):
        self.camera = make_camera()
        self.user = User.objects.create_user(username="reviewer", password="pass")

    def test_default_status_is_pending(self):
        img = CameraImage.objects.create(
            camera=self.camera,
            image="camera_images/test.jpg",
        )
        self.assertEqual(img.status, CameraImage.Status.PENDING)

    def test_approve_sets_status_and_reviewer(self):
        img = make_camera_image(self.camera, status=CameraImage.Status.PENDING)
        img.approve(self.user)
        img.refresh_from_db()
        self.assertEqual(img.status, CameraImage.Status.APPROVED)
        self.assertEqual(img.reviewed_by, self.user)
        self.assertIsNotNone(img.reviewed_at)

    def test_reject_sets_status_and_reviewer(self):
        img = make_camera_image(self.camera, status=CameraImage.Status.PENDING)
        img.reject(self.user)
        img.refresh_from_db()
        self.assertEqual(img.status, CameraImage.Status.REJECTED)
        self.assertEqual(img.reviewed_by, self.user)
        self.assertIsNotNone(img.reviewed_at)
