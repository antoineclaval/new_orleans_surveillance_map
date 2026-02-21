"""
Views for camera mapping application.
"""

from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView

from .forms import CameraReportForm
from .models import Camera

_MOBILE_UA_KEYWORDS = ("mobile", "android", "iphone", "ipad", "ipod")


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

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class ReportSuccessView(TemplateView):
    """
    Success page after camera submission.
    """

    template_name = "report_success.html"
