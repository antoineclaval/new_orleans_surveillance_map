"""
DRF API views for cameras.
"""

from rest_framework import generics

from .models import Camera
from .serializers import CameraDetailSerializer, CameraGeoSerializer


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
        queryset = Camera.objects.filter(status=Camera.Status.VETTED)

        # Filter by facial recognition
        facial_recognition = self.request.query_params.get("facial_recognition")
        if facial_recognition is not None:
            queryset = queryset.filter(
                facial_recognition=facial_recognition.lower() == "true"
            )

        # Filter by has associated shop
        has_shop = self.request.query_params.get("has_shop")
        if has_shop is not None:
            if has_shop.lower() == "true":
                queryset = queryset.exclude(associated_shop="")
            else:
                queryset = queryset.filter(associated_shop="")

        # Filter by camera type
        camera_type = self.request.query_params.get("type")
        if camera_type:
            queryset = queryset.filter(camera_type=camera_type)

        return queryset


class CameraDetailAPIView(generics.RetrieveAPIView):
    """
    Returns details for a single camera.
    """

    queryset = Camera.objects.filter(status=Camera.Status.VETTED)
    serializer_class = CameraDetailSerializer
    lookup_field = "id"
