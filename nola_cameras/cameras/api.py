"""
DRF API views for cameras.
"""

from django.db.models import Prefetch
from rest_framework import generics

from .models import Camera, CameraImage
from .serializers import CameraGeoSerializer


class CameraListAPIView(generics.ListAPIView):
    """
    Returns all vetted cameras as GeoJSON for map display.

    Supports filtering via query parameters:
    - facial_recognition: true/false
    - has_shop: true/false
    - type: project_nola/nopd/private/unknown
    """

    serializer_class = CameraGeoSerializer

    def get_queryset(self):
        queryset = Camera.objects.filter(status=Camera.Status.VETTED).prefetch_related(
            Prefetch(
                "images",
                queryset=CameraImage.objects.filter(status=CameraImage.Status.APPROVED),
                to_attr="_approved_images",
            )
        )

        facial_recognition = self.request.query_params.get("facial_recognition")
        if facial_recognition is not None:
            queryset = queryset.filter(
                facial_recognition=facial_recognition.lower() == "true"
            )

        has_shop = self.request.query_params.get("has_shop")
        if has_shop is not None:
            if has_shop.lower() == "true":
                queryset = queryset.exclude(associated_shop="")
            else:
                queryset = queryset.filter(associated_shop="")

        camera_type = self.request.query_params.get("type")
        if camera_type:
            queryset = queryset.filter(camera_type=camera_type)

        return queryset
