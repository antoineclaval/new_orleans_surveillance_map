"""
Camera model for NOLA surveillance camera mapping.
"""

import uuid

from django.contrib.auth.models import User
from django.contrib.gis.db import models
from django.utils import timezone


class Camera(models.Model):
    """
    Represents a surveillance camera in New Orleans.
    """

    class Status(models.TextChoices):
        VETTED = "vetted", "Vetted"
        PENDING = "pending", "Pending Review"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Location information
    cross_road = models.CharField(
        max_length=255,
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

    # Image upload
    image = models.ImageField(
        upload_to="camera_images/%Y/%m/",
        blank=True,
        null=True,
        help_text="Photo of the camera",
    )
    image_2 = models.ImageField(
        upload_to="camera_images/%Y/%m/",
        blank=True,
        null=True,
        help_text="Photo of the camera and its surroundings",
    )
    image_3 = models.ImageField(
        upload_to="camera_images/%Y/%m/",
        blank=True,
        null=True,
        help_text="Photo of a Project Nola sign (if present)",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-reported_at"]
        verbose_name = "Camera"
        verbose_name_plural = "Cameras"

    def __str__(self):
        return f"{self.cross_road} ({self.get_status_display()})"

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
