"""
Django admin configuration for Camera model.
"""

from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from django.contrib.gis.geos import Point
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from import_export import fields, resources
from import_export.admin import ImportExportMixin

from .models import AboutSection, Announcement, Camera, CameraImage, CorrectionProposal


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

    def import_obj(self, obj, data, dry_run, **kwargs):
        super().import_obj(obj, data, dry_run, **kwargs)
        lat = data.get("latitude")
        lon = data.get("longitude")
        if lat and lon:
            try:
                obj.location = Point(float(lon), float(lat), srid=4326)
            except (ValueError, TypeError):
                pass

    class Meta:
        model = Camera
        fields = (
            "id",
            "osm_id",
            "cross_road",
            "street_address",
            "latitude",
            "longitude",
            "facial_recognition",
            "associated_shop",
            "camera_type",
            "manufacturer",
            "direction",
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
    for camera in queryset:
        camera.approve(request.user)
        camera.images.filter(status=CameraImage.Status.PENDING).update(
            status=CameraImage.Status.APPROVED,
            reviewed_at=timezone.now(),
            reviewed_by=request.user,
        )


@admin.action(description="Reject selected cameras")
def reject_cameras(modeladmin, request, queryset):
    for camera in queryset:
        camera.reject(request.user)


@admin.action(description="Mark as pending review")
def mark_pending(modeladmin, request, queryset):
    queryset.update(status=Camera.Status.PENDING, vetted_at=None, vetted_by=None)


@admin.action(description="Approve selected images")
def approve_images(modeladmin, request, queryset):
    for img in queryset:
        img.approve(request.user)


@admin.action(description="Reject selected images")
def reject_images(modeladmin, request, queryset):
    for img in queryset:
        img.reject(request.user)


@admin.action(description="Accept selected correction proposals")
def accept_corrections(modeladmin, request, queryset):
    for proposal in queryset:
        proposal.accept(request.user)


@admin.action(description="Reject selected correction proposals")
def reject_corrections(modeladmin, request, queryset):
    for proposal in queryset:
        proposal.reject(request.user)


class CameraImageInline(admin.TabularInline):
    model = CameraImage
    extra = 1
    readonly_fields = ["image_preview_inline", "proposed_at", "proposed_by", "reviewed_at", "reviewed_by"]
    fields = ["image_preview_inline", "image", "photo_type", "status", "proposed_by", "proposed_at", "reviewed_at", "reviewed_by"]
    show_change_link = True

    def image_preview_inline(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 80px; max-width: 120px; object-fit: cover;"/>',
                obj.image.url,
            )
        return "-"
    image_preview_inline.short_description = "Preview"


class CorrectionProposalInline(admin.TabularInline):
    model = CorrectionProposal
    extra = 0
    readonly_fields = ["message", "status", "proposed_by", "proposed_at", "reviewed_at", "reviewed_by"]
    fields = ["message", "status", "proposed_by", "proposed_at", "reviewed_at", "reviewed_by"]
    show_change_link = True
    can_delete = False


@admin.register(Camera)
class CameraAdmin(ImportExportMixin, GISModelAdmin):
    """Admin interface for Camera model with map widget and export."""

    resource_class = CameraResource
    inlines = [CameraImageInline, CorrectionProposalInline]

    list_display = [
        "short_id",
        "cross_road",
        "status_badge",
        "camera_type_badge",
        "facial_recognition_badge",
        "associated_shop",
        "reported_at",
        "image_preview",
    ]
    list_display_links = ["short_id"]
    list_filter = [
        "status",
        "camera_type",
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
        "osm_id",
    ]
    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "reported_at",
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
                    "camera_type",
                    "manufacturer",
                    "direction",
                    "facial_recognition",
                    "associated_shop",
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
                "fields": ("id", "osm_id", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    gis_widget_kwargs = {
        "attrs": {
            "default_lat": 29.9511,
            "default_lon": -90.0715,
            "default_zoom": 12,
        },
    }

    def short_id(self, obj):
        return str(obj.id)[:8]

    short_id.short_description = "ID"
    short_id.admin_order_field = "id"

    def status_badge(self, obj):
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

    def camera_type_badge(self, obj):
        colors = {
            Camera.CameraType.PROJECT_NOLA: "#6b46c1",
            Camera.CameraType.NOPD: "#2563eb",
            Camera.CameraType.PRIVATE: "#ea580c",
            Camera.CameraType.TRAFFIC: "#16a34a",
            Camera.CameraType.ALPR: "#b45309",
            Camera.CameraType.UNKNOWN: "#6b7280",
        }
        color = colors.get(obj.camera_type, "#6b7280")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color,
            obj.get_camera_type_display(),
        )

    camera_type_badge.short_description = "Type"
    camera_type_badge.admin_order_field = "camera_type"

    def facial_recognition_badge(self, obj):
        if obj.facial_recognition:
            return format_html(
                '<span style="background-color: #dc2626; color: white; padding: 3px 8px; '
                'border-radius: 4px; font-size: 11px;">FR</span>'
            )
        return ""

    facial_recognition_badge.short_description = "FR"
    facial_recognition_badge.admin_order_field = "facial_recognition"

    def image_preview(self, obj):
        first = obj.images.filter(status=CameraImage.Status.APPROVED).first() or obj.images.first()
        if first and first.image:
            return format_html(
                '<img src="{}" style="max-height: 40px; max-width: 60px; object-fit: cover;"/>',
                first.image.url,
            )
        return "-"

    image_preview.short_description = "Photo"

    def save_model(self, request, obj, form, change):
        if obj.status == Camera.Status.VETTED and not obj.vetted_by:
            obj.vetted_by = request.user
            obj.vetted_at = timezone.now()
        super().save_model(request, obj, form, change)
        if obj.status == Camera.Status.VETTED:
            obj.images.filter(status=CameraImage.Status.PENDING).update(
                status=CameraImage.Status.APPROVED,
                reviewed_at=timezone.now(),
                reviewed_by=request.user,
            )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("vetted_by")


@admin.register(CameraImage)
class CameraImageAdmin(admin.ModelAdmin):
    list_display = [
        "short_id",
        "camera_link",
        "photo_type",
        "status_badge",
        "proposed_by",
        "proposed_at",
        "image_preview",
    ]
    list_filter = ["status", "photo_type", "proposed_at"]
    search_fields = ["camera__cross_road", "camera__street_address", "proposed_by"]
    readonly_fields = ["id", "proposed_at", "reviewed_at", "reviewed_by", "image_preview_large"]
    actions = [approve_images, reject_images]
    date_hierarchy = "proposed_at"

    fieldsets = (
        ("Photo", {"fields": ("camera", "image", "image_preview_large", "photo_type")}),
        ("Status", {"fields": ("status", "notes")}),
        ("Proposer Information", {"fields": ("proposed_by", "proposed_at"), "classes": ("collapse",)}),
        ("Review Information", {"fields": ("reviewed_at", "reviewed_by"), "classes": ("collapse",)}),
        ("Metadata", {"fields": ("id",), "classes": ("collapse",)}),
    )

    def short_id(self, obj):
        return str(obj.id)[:8]
    short_id.short_description = "ID"

    def camera_link(self, obj):
        url = reverse("admin:cameras_camera_change", args=[obj.camera_id])
        return format_html('<a href="{}">{}</a>', url, obj.camera)
    camera_link.short_description = "Camera"

    def status_badge(self, obj):
        colors = {
            CameraImage.Status.APPROVED: "#22c55e",
            CameraImage.Status.PENDING:  "#eab308",
            CameraImage.Status.REJECTED: "#ef4444",
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

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 40px; max-width: 60px; object-fit: cover;"/>',
                obj.image.url,
            )
        return "-"
    image_preview.short_description = "Photo"

    def image_preview_large(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 300px; max-width: 400px;"/>',
                obj.image.url,
            )
        return "No image uploaded"
    image_preview_large.short_description = "Preview"

    def save_model(self, request, obj, form, change):
        if obj.status == CameraImage.Status.APPROVED and not obj.reviewed_by:
            obj.reviewed_by = request.user
            obj.reviewed_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(CorrectionProposal)
class CorrectionProposalAdmin(admin.ModelAdmin):
    list_display = [
        "short_id",
        "camera_link",
        "status_badge",
        "proposed_by",
        "proposed_at",
        "message_excerpt",
    ]
    list_filter = ["status", "proposed_at"]
    search_fields = ["camera__cross_road", "camera__street_address", "proposed_by", "message"]
    readonly_fields = ["id", "proposed_at", "reviewed_at", "reviewed_by"]
    actions = [accept_corrections, reject_corrections]
    date_hierarchy = "proposed_at"

    fieldsets = (
        ("Proposal", {"fields": ("camera", "message")}),
        ("Status", {"fields": ("status", "notes")}),
        ("Proposer Information", {"fields": ("proposed_by", "proposed_at"), "classes": ("collapse",)}),
        ("Review Information", {"fields": ("reviewed_at", "reviewed_by"), "classes": ("collapse",)}),
        ("Metadata", {"fields": ("id",), "classes": ("collapse",)}),
    )

    def short_id(self, obj):
        return str(obj.id)[:8]
    short_id.short_description = "ID"

    def camera_link(self, obj):
        url = reverse("admin:cameras_camera_change", args=[obj.camera_id])
        return format_html('<a href="{}">{}</a>', url, obj.camera)
    camera_link.short_description = "Camera"

    def status_badge(self, obj):
        colors = {
            CorrectionProposal.Status.ACCEPTED: "#22c55e",
            CorrectionProposal.Status.PENDING:  "#eab308",
            CorrectionProposal.Status.REJECTED: "#ef4444",
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

    def message_excerpt(self, obj):
        return obj.message[:80] + "…" if len(obj.message) > 80 else obj.message
    message_excerpt.short_description = "Message"

    def save_model(self, request, obj, form, change):
        if obj.status in (CorrectionProposal.Status.ACCEPTED, CorrectionProposal.Status.REJECTED):
            if not obj.reviewed_by:
                obj.reviewed_by = request.user
                obj.reviewed_at = timezone.now()
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("camera", "reviewed_by")


@admin.register(AboutSection)
class AboutSectionAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not AboutSection.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ["title", "published_at", "is_active"]
    list_filter = ["is_active"]
    list_editable = ["is_active"]
    date_hierarchy = "published_at"


# Customize admin site
admin.site.site_header = "New Orleans surveillance map admin"
admin.site.site_title = "New Orleans Cameras"
admin.site.index_title = "Camera Management"
