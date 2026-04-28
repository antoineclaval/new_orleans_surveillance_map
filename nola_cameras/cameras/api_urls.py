"""
API URL configuration for cameras.
"""

from django.urls import path

from . import api

urlpatterns = [
    path("cameras/", api.CameraListAPIView.as_view(), name="camera-list"),
]
