"""
URL configuration for cameras app.
"""

from django.urls import path

from . import views

urlpatterns = [
    path("", views.MapView.as_view(), name="map"),
    path("report/", views.CameraReportView.as_view(), name="report"),
    path("report/success/", views.ReportSuccessView.as_view(), name="report-success"),
    path("cameras/<uuid:camera_id>/propose-photo/", views.ProposePhotoView.as_view(), name="propose-photo"),
    path("cameras/<uuid:camera_id>/propose-photo/success/", views.ProposePhotoSuccessView.as_view(), name="propose-photo-success"),
]
