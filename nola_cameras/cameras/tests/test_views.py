import tempfile

from django.test import TestCase, override_settings
from django.urls import reverse

from cameras.models import Camera, CameraImage

from .utils import make_camera, make_image_file


class MapViewTests(TestCase):
    def test_map_view_renders(self):
        response = self.client.get(reverse("map"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "map.html")

    def test_map_view_pending_count_in_context(self):
        make_camera(status=Camera.Status.PENDING)
        make_camera(status=Camera.Status.PENDING)
        response = self.client.get(reverse("map"))
        self.assertEqual(response.context["pending_count"], 2)

    def test_map_view_pending_count_excludes_vetted(self):
        make_camera(status=Camera.Status.VETTED)
        make_camera(status=Camera.Status.PENDING)
        response = self.client.get(reverse("map"))
        self.assertEqual(response.context["pending_count"], 1)


class ReportViewTests(TestCase):
    def test_report_view_get(self):
        response = self.client.get(reverse("report"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)

    def test_report_view_post_valid_redirects(self):
        data = {
            "cross_road": "St Charles Ave & Canal St",
            "latitude": "29.9545",
            "longitude": "-90.0790",
            "website": "",
        }
        response = self.client.post(reverse("report"), data)
        self.assertRedirects(response, reverse("report-success"))

    def test_report_view_post_invalid_stays(self):
        data = {
            "cross_road": "",
            "latitude": "29.9545",
            "longitude": "-90.0790",
            "website": "",
        }
        response = self.client.post(reverse("report"), data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)

    def test_report_view_mobile_template(self):
        response = self.client.get(
            reverse("report"),
            HTTP_USER_AGENT="Mozilla/5.0 (Linux; Android 10; SM-G975U)",
        )
        self.assertTemplateUsed(response, "report_mobile.html")

    def test_report_view_desktop_template(self):
        response = self.client.get(
            reverse("report"),
            HTTP_USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        )
        self.assertTemplateUsed(response, "report.html")


class ReportSuccessViewTests(TestCase):
    def test_report_success_view_renders(self):
        response = self.client.get(reverse("report-success"))
        self.assertEqual(response.status_code, 200)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class CameraReportViewImageTests(TestCase):
    def test_post_with_images_creates_camera_images(self):
        data = {
            "cross_road": "St Charles Ave & Canal St",
            "latitude": "29.9545",
            "longitude": "-90.0790",
            "website": "",
        }
        files = {
            "image_close_up": make_image_file("close_up.jpg"),
            "image_surrounding": make_image_file("surrounding.jpg"),
        }
        self.client.post(reverse("report"), {**data, **files})
        camera = Camera.objects.get(cross_road="St Charles Ave & Canal St")
        images = CameraImage.objects.filter(camera=camera)
        self.assertEqual(images.count(), 2)
        types = set(images.values_list("photo_type", flat=True))
        self.assertIn(CameraImage.PhotoType.CLOSE_UP, types)
        self.assertIn(CameraImage.PhotoType.SURROUNDING, types)
        self.assertTrue(all(img.status == CameraImage.Status.PENDING for img in images))


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ProposePhotoViewTests(TestCase):
    def setUp(self):
        self.vetted = make_camera(cross_road="Vetted Camera")
        self.pending = make_camera(status=Camera.Status.PENDING, cross_road="Pending Camera")

    def test_get_renders_with_camera_context(self):
        url = reverse("propose-photo", kwargs={"camera_id": self.vetted.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "propose_photo.html")
        self.assertEqual(response.context["camera"], self.vetted)

    def test_get_404_for_pending_camera(self):
        url = reverse("propose-photo", kwargs={"camera_id": self.pending.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_post_valid_redirects_to_success(self):
        url = reverse("propose-photo", kwargs={"camera_id": self.vetted.pk})
        response = self.client.post(url, {
            "image": make_image_file(),
            "photo_type": CameraImage.PhotoType.CLOSE_UP,
            "proposed_by": "",
            "website": "",
        })
        self.assertRedirects(response, reverse("propose-photo-success", kwargs={"camera_id": self.vetted.pk}))
        self.assertEqual(CameraImage.objects.filter(camera=self.vetted).count(), 1)

    def test_post_missing_image_stays_on_form(self):
        url = reverse("propose-photo", kwargs={"camera_id": self.vetted.pk})
        response = self.client.post(url, {
            "photo_type": CameraImage.PhotoType.CLOSE_UP,
            "proposed_by": "",
            "website": "",
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)


class ProposePhotoSuccessViewTests(TestCase):
    def setUp(self):
        self.vetted = make_camera()
        self.pending = make_camera(status=Camera.Status.PENDING, cross_road="Pending")

    def test_renders_with_camera_context(self):
        url = reverse("propose-photo-success", kwargs={"camera_id": self.vetted.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "propose_photo_success.html")
        self.assertEqual(response.context["camera"], self.vetted)

    def test_404_for_pending_camera(self):
        url = reverse("propose-photo-success", kwargs={"camera_id": self.pending.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
