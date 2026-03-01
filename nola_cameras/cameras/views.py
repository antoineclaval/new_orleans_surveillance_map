"""
Views for camera mapping application.
"""

from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView

from .forms import CameraReportForm
from .models import Camera

_MOBILE_UA_KEYWORDS = ("mobile", "android", "iphone", "ipad", "ipod")

_NOLA_DEFAULT_LAT = 29.9511
_NOLA_DEFAULT_LNG = -90.0715
_NOLA_DEFAULT_ZOOM = 13


class MapView(TemplateView):
    """
    Main map view showing all vetted cameras.
    """

    template_name = "map.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pending_count"] = Camera.objects.filter(
            status=Camera.Status.PENDING
        ).count()
        return context


class CameraReportView(FormView):
    """
    Public form for submitting new camera sightings.
    """

    template_name = "report.html"
    form_class = CameraReportForm
    success_url = reverse_lazy("report-success")

    def get_template_names(self):
        ua = self.request.META.get("HTTP_USER_AGENT", "").lower()
        if any(kw in ua for kw in _MOBILE_UA_KEYWORDS):
            return ["report_mobile.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            init_lat = float(self.request.GET.get("lat", _NOLA_DEFAULT_LAT))
            init_lng = float(self.request.GET.get("lng", _NOLA_DEFAULT_LNG))
            init_zoom = int(self.request.GET.get("zoom", _NOLA_DEFAULT_ZOOM))
        except (TypeError, ValueError):
            init_lat, init_lng, init_zoom = _NOLA_DEFAULT_LAT, _NOLA_DEFAULT_LNG, _NOLA_DEFAULT_ZOOM
        context["init_lat"] = max(-90.0, min(90.0, init_lat))
        context["init_lng"] = max(-180.0, min(180.0, init_lng))
        context["init_zoom"] = max(1, min(19, init_zoom))
        context["pinned"] = self.request.GET.get("pinned") == "1"
        return context

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class ReportSuccessView(TemplateView):
    """
    Success page after camera submission.
    """

    template_name = "report_success.html"
