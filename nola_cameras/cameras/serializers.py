"""
DRF serializers for camera API.
"""

from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from .models import Camera, CameraImage


class CameraGeoSerializer(GeoFeatureModelSerializer):
    """
    GeoJSON serializer for cameras.
    Returns cameras as GeoJSON features for map display.
    """

    photos = serializers.SerializerMethodField()

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
            "photos",
        ]

    def get_photos(self, obj):
        request = self.context.get("request")
        imgs = getattr(obj, "_approved_images", None)
        if imgs is None:
            imgs = list(obj.images.filter(status=CameraImage.Status.APPROVED))
        result = []
        for img in imgs:
            if img.image:
                url = request.build_absolute_uri(img.image.url) if request else img.image.url
                result.append({"url": url, "type": img.photo_type})
        return result
