from django.test import TestCase
from django.urls import reverse

from cameras.models import Camera

from .utils import make_camera


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
