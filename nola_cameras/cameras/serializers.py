"""
DRF serializers for camera API.
"""

from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from .models import Camera


class CameraGeoSerializer(GeoFeatureModelSerializer):
    """
    GeoJSON serializer for cameras.
    Returns cameras as GeoJSON features for map display.
    """

    class Meta:
        model = Camera
        geo_field = "location"
        fields = [
            "id",
            "cross_road",
            "street_address",
            "facial_recognition",
            "associated_shop",
            "camera_type",
            "image",
            "image_2",
            "image_3",
        ]


class CameraDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for single camera view.
    """

    latitude = serializers.FloatField(read_only=True)
    longitude = serializers.FloatField(read_only=True)

    class Meta:
        model = Camera
        fields = [
            "id",
            "cross_road",
            "street_address",
            "latitude",
            "longitude",
            "facial_recognition",
            "associated_shop",
            "camera_type",
            "image",
            "reported_at",
        ]
