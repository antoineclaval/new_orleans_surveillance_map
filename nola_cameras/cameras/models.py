"""
Camera model for New Orleans surveillance camera mapping.
"""

import uuid
from pathlib import Path

from ckeditor.fields import RichTextField
from django.contrib.auth.models import User
from django.contrib.gis.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class Camera(models.Model):
    """
    Represents a surveillance camera in New Orleans.
    """

    class Status(models.TextChoices):
        VETTED = "vetted", "Vetted"
        PENDING = "pending", "Pending Review"
        REJECTED = "rejected", "Rejected"

    class CameraType(models.TextChoices):
        PROJECT_NOLA = "project_nola", "Project NOLA"
        NOPD         = "nopd",         "NOPD"
        PRIVATE      = "private",      "Private"
        TRAFFIC      = "traffic",      "Traffic"
        ALPR         = "alpr",         "ALPR"
        UNKNOWN      = "unknown",      "Unknown"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    osm_id = models.BigIntegerField(
        null=True,
        blank=True,
        unique=True,
        help_text="OpenStreetMap node ID (for deduplication and future OSM contribution)",
    )

    # Location information
    cross_road = models.CharField(
        max_length=255,
        blank=True,
        help_text="Nearest intersection, e.g. 'Canal St & Bourbon St'",
    )
    street_address = models.CharField(
        max_length=255,
        blank=True,
        help_text="Specific address if known",
    )
    location = models.PointField(
        help_text="Geographic coordinates (longitude, latitude)",
        srid=4326,
    )

    # Camera details
    facial_recognition = models.BooleanField(
        default=False,
        help_text="Does this camera have facial recognition capability?",
    )
    associated_shop = models.CharField(
        max_length=255,
        blank=True,
        help_text="Business name if this is a private camera",
    )

    # Camera type / operator
    camera_type = models.CharField(
        max_length=20,
        choices=CameraType.choices,
        default=CameraType.UNKNOWN,
        db_index=True,
    )
    manufacturer = models.CharField(
        max_length=255,
        blank=True,
        help_text="Camera manufacturer (e.g. 'Neology, Inc.')",
    )
    direction = models.CharField(
        max_length=20,
        blank=True,
        help_text="Camera pointing direction in degrees (0-359) or cardinal",
    )

    # Status and review
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    notes = models.TextField(
        blank=True,
        help_text="Admin notes about this camera",
    )

    # Reporter information
    reported_by = models.CharField(
        max_length=255,
        blank=True,
        help_text="Email or name of person who reported this camera",
    )
    reported_at = models.DateTimeField(default=timezone.now)

    # Vetting information
    vetted_at = models.DateTimeField(null=True, blank=True)
    vetted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vetted_cameras",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-reported_at"]
        verbose_name = "Camera"
        verbose_name_plural = "Cameras"

    def clean(self):
        if not any([self.cross_road, self.street_address, self.associated_shop]):
            raise ValidationError(
                "At least one of cross_road, street_address, or associated_shop must be provided."
            )

    def __str__(self):
        label = self.cross_road or self.street_address or self.associated_shop
        return f"{label} ({self.get_status_display()})"

    @property
    def latitude(self):
        return self.location.y if self.location else None

    @property
    def longitude(self):
        return self.location.x if self.location else None

    def approve(self, user):
        """Mark this camera as vetted."""
        self.status = self.Status.VETTED
        self.vetted_at = timezone.now()
        self.vetted_by = user
        self.save()

    def reject(self, user):
        """Mark this camera as rejected."""
        self.status = self.Status.REJECTED
        self.vetted_at = timezone.now()
        self.vetted_by = user
        self.save()


def _camera_image_upload_to(instance, filename):
    ext = Path(filename).suffix.lower() or ".jpg"
    n = CameraImage.objects.filter(camera_id=instance.camera_id).count() + 1
    date = timezone.now().strftime("%Y%m%d")
    return f"camera_images/eos-camera-{instance.camera_id}-{date}-{n}{ext}"


class CameraImage(models.Model):
    class Status(models.TextChoices):
        PENDING  = "pending",  "Pending Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    class PhotoType(models.TextChoices):
        SURROUNDING       = "surrounding",       "Surrounding"
        CLOSE_UP          = "close_up",          "Close Up"
        PROJECT_NOLA_SIGN = "project_nola_sign", "Project NOLA Sign"

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    camera      = models.ForeignKey(Camera, on_delete=models.CASCADE, related_name="images")
    image       = models.ImageField(upload_to=_camera_image_upload_to)
    photo_type  = models.CharField(max_length=30, choices=PhotoType.choices, default=PhotoType.CLOSE_UP)
    status      = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    proposed_by = models.CharField(max_length=255, blank=True)
    proposed_at = models.DateTimeField(default=timezone.now)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_images"
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["photo_type", "-proposed_at"]
        verbose_name = "Camera Image"
        verbose_name_plural = "Camera Images"

    def __str__(self):
        return f"{self.get_photo_type_display()} — {self.camera} ({self.get_status_display()})"

    def approve(self, user):
        self.status = self.Status.APPROVED
        self.reviewed_at = timezone.now()
        self.reviewed_by = user
        self.save()

    def reject(self, user):
        self.status = self.Status.REJECTED
        self.reviewed_at = timezone.now()
        self.reviewed_by = user
        self.save()


class CorrectionProposal(models.Model):
    class Status(models.TextChoices):
        PENDING  = "pending",  "Pending Review"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    camera      = models.ForeignKey(Camera, on_delete=models.CASCADE, related_name="correction_proposals")
    message     = models.TextField()
    status      = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    proposed_by = models.CharField(max_length=255, blank=True)
    proposed_at = models.DateTimeField(default=timezone.now)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_corrections"
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-proposed_at"]
        verbose_name = "Correction Proposal"
        verbose_name_plural = "Correction Proposals"

    def __str__(self):
        label = self.camera.cross_road or self.camera.street_address or self.camera.associated_shop
        return f"Correction for {label} ({self.get_status_display()})"

    def accept(self, user):
        self.status = self.Status.ACCEPTED
        self.reviewed_at = timezone.now()
        self.reviewed_by = user
        self.save()

    def reject(self, user):
        self.status = self.Status.REJECTED
        self.reviewed_at = timezone.now()
        self.reviewed_by = user
        self.save()


class AboutSection(models.Model):
    """Singleton: project About/description text."""

    content = RichTextField(
        help_text="Description shown in the 'About' tab of the info overlay"
    )

    class Meta:
        verbose_name = "About Section"
        verbose_name_plural = "About Section"

    def __str__(self):
        return "About Section"


class Announcement(models.Model):
    """An individual announcement shown in the info overlay."""

    title = models.CharField(max_length=255)
    content = RichTextField()
    published_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-published_at"]
        verbose_name = "Announcement"
        verbose_name_plural = "Announcements"

    def __str__(self):
        return self.title
