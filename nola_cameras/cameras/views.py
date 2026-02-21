"""
Views for camera mapping application.
"""

from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView

from .forms import CameraReportForm


class MapView(TemplateView):
    """
    Main map view showing all vetted cameras.
    """

    template_name = "map.html"


class CameraReportView(FormView):
    """
    Public form for submitting new camera sightings.
    """

    template_name = "report.html"
    form_class = CameraReportForm
    success_url = reverse_lazy("report-success")

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class ReportSuccessView(TemplateView):
    """
    Success page after camera submission.
    """

    template_name = "report_success.html"
