"""
URL configuration for cameras app.
"""

from django.urls import path

from . import views

urlpatterns = [
    path("", views.MapView.as_view(), name="map"),
    path("report/", views.CameraReportView.as_view(), name="report"),
    path("report/success/", views.ReportSuccessView.as_view(), name="report-success"),
]
