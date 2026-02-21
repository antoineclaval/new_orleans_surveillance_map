"""
Django admin configuration for Camera model.
"""

from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from django.utils import timezone
from django.utils.html import format_html
from import_export import fields, resources
from import_export.admin import ExportMixin

from .models import Camera


class CameraResource(resources.ModelResource):
    """Resource for CSV/GeoJSON export."""

    latitude = fields.Field(column_name="latitude")
    longitude = fields.Field(column_name="longitude")
    vetted_by_username = fields.Field(column_name="vetted_by")

    def dehydrate_latitude(self, camera):
        return camera.location.y if camera.location else ""

    def dehydrate_longitude(self, camera):
        return camera.location.x if camera.location else ""

    def dehydrate_vetted_by_username(self, camera):
        return camera.vetted_by.username if camera.vetted_by_id else ""

    class Meta:
        model = Camera
        fields = (
            "id",
            "cross_road",
            "street_address",
            "latitude",
            "longitude",
            "facial_recognition",
            "associated_shop",
            "status",
            "reported_by",
            "reported_at",
            "vetted_at",
            "vetted_by_username",
            "notes",
        )
        export_order = fields


@admin.action(description="Approve selected cameras")
def approve_cameras(modeladmin, request, queryset):
    """Bulk approve selected cameras."""
    for camera in queryset:
        camera.status = Camera.Status.VETTED
        camera.vetted_at = timezone.now()
        camera.vetted_by = request.user
        camera.save()


@admin.action(description="Reject selected cameras")
def reject_cameras(modeladmin, request, queryset):
    """Bulk reject selected cameras."""
    for camera in queryset:
        camera.status = Camera.Status.REJECTED
        camera.vetted_at = timezone.now()
        camera.vetted_by = request.user
        camera.save()


@admin.action(description="Mark as pending review")
def mark_pending(modeladmin, request, queryset):
    """Mark selected cameras as pending."""
    queryset.update(status=Camera.Status.PENDING, vetted_at=None, vetted_by=None)


@admin.register(Camera)
class CameraAdmin(ExportMixin, GISModelAdmin):
    """Admin interface for Camera model with map widget and export."""

    resource_class = CameraResource

    list_display = [
        "cross_road",
        "status_badge",
        "facial_recognition_badge",
        "associated_shop",
        "reported_at",
        "image_preview",
    ]
    list_filter = [
        "status",
        "facial_recognition",
        ("vetted_at", admin.EmptyFieldListFilter),
        "reported_at",
    ]
    search_fields = [
        "cross_road",
        "street_address",
        "associated_shop",
        "reported_by",
        "notes",
    ]
    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "reported_at",
        "image_preview_large",
        "image_preview_large_2",
        "image_preview_large_3",
    ]
    date_hierarchy = "reported_at"
    actions = [approve_cameras, reject_cameras, mark_pending]

    fieldsets = (
        (
            "Location",
            {
                "fields": ("cross_road", "street_address", "location"),
            },
        ),
        (
            "Camera Details",
            {
                "fields": (
                    "facial_recognition",
                    "associated_shop",
                    "image",
                    "image_preview_large",
                    "image_2",
                    "image_preview_large_2",
                    "image_3",
                    "image_preview_large_3",
                ),
            },
        ),
        (
            "Status",
            {
                "fields": ("status", "notes"),
            },
        ),
        (
            "Reporter Information",
            {
                "fields": ("reported_by", "reported_at"),
                "classes": ("collapse",),
            },
        ),
        (
            "Review Information",
            {
                "fields": ("vetted_at", "vetted_by"),
                "classes": ("collapse",),
            },
        ),
        (
            "Metadata",
            {
                "fields": ("id", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    # OpenStreetMap as default map widget
    gis_widget_kwargs = {
        "attrs": {
            "default_lat": 29.9511,  # New Orleans center
            "default_lon": -90.0715,
            "default_zoom": 12,
        },
    }

    def status_badge(self, obj):
        """Display status as colored badge."""
        colors = {
            Camera.Status.VETTED: "#22c55e",
            Camera.Status.PENDING: "#eab308",
            Camera.Status.REJECTED: "#ef4444",
        }
        color = colors.get(obj.status, "#6b7280")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_badge.short_description = "Status"
    status_badge.admin_order_field = "status"

    def facial_recognition_badge(self, obj):
        """Display facial recognition status."""
        if obj.facial_recognition:
            return format_html(
                '<span style="background-color: #dc2626; color: white; padding: 3px 8px; '
                'border-radius: 4px; font-size: 11px;">FR</span>'
            )
        return ""

    facial_recognition_badge.short_description = "FR"
    facial_recognition_badge.admin_order_field = "facial_recognition"

    def image_preview(self, obj):
        """Display thumbnail in list view (first available image)."""
        img = obj.image or obj.image_2 or obj.image_3
        if img:
            return format_html(
                '<img src="{}" style="max-height: 40px; max-width: 60px; object-fit: cover;"/>',
                img.url,
            )
        return "-"

    image_preview.short_description = "Photo"

    def image_preview_large(self, obj):
        """Display larger image in detail view."""
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 300px; max-width: 400px;"/>',
                obj.image.url,
            )
        return "No image uploaded"

    image_preview_large.short_description = "Image Preview"

    def image_preview_large_2(self, obj):
        """Display second image in detail view."""
        if obj.image_2:
            return format_html(
                '<img src="{}" style="max-height: 300px; max-width: 400px;"/>',
                obj.image_2.url,
            )
        return "No image uploaded"

    image_preview_large_2.short_description = "Image 2 Preview"

    def image_preview_large_3(self, obj):
        """Display third image in detail view."""
        if obj.image_3:
            return format_html(
                '<img src="{}" style="max-height: 300px; max-width: 400px;"/>',
                obj.image_3.url,
            )
        return "No image uploaded"

    image_preview_large_3.short_description = "Image 3 Preview"

    def save_model(self, request, obj, form, change):
        """Auto-fill vetted_by when status changes to vetted."""
        if obj.status == Camera.Status.VETTED and not obj.vetted_by:
            obj.vetted_by = request.user
            obj.vetted_at = timezone.now()
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        """Show pending cameras first by default."""
        qs = super().get_queryset(request)
        return qs.select_related("vetted_by")


# Customize admin site
admin.site.site_header = "New Orleans Camera Mapping Admin"
admin.site.site_title = "New Orleans Cameras"
admin.site.index_title = "Camera Management"
