"""
Forms for camera submission.
"""

from django import forms
from django.contrib.gis.geos import Point

from .models import Camera, CameraImage

_MAX_IMAGE_SIZE_MB = 20


def validate_image_file_size(image):
    if image.size > _MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise forms.ValidationError(f"Image too large. Maximum size is {_MAX_IMAGE_SIZE_MB} MB.")


class CameraReportForm(forms.ModelForm):
    """
    Form for public camera submissions.
    Includes honeypot field for spam prevention.
    """

    # Hidden honeypot field - should remain empty
    website = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "autocomplete": "off",
            "tabindex": "-1",
            "style": "position: absolute; left: -9999px;",
        }),
        label="",
    )

    latitude = forms.FloatField(
        widget=forms.HiddenInput(),
        min_value=-90,
        max_value=90,
    )
    longitude = forms.FloatField(
        widget=forms.HiddenInput(),
        min_value=-180,
        max_value=180,
    )

    # Image slots — not model fields, handled in view
    image_close_up = forms.ImageField(
        required=False,
        validators=[validate_image_file_size],
        widget=forms.FileInput(attrs={"class": "form-file", "accept": "image/*"}),
    )
    image_surrounding = forms.ImageField(
        required=False,
        validators=[validate_image_file_size],
        widget=forms.FileInput(attrs={"class": "form-file", "accept": "image/*"}),
    )
    image_project_nola_sign = forms.ImageField(
        required=False,
        validators=[validate_image_file_size],
        widget=forms.FileInput(attrs={"class": "form-file", "accept": "image/*"}),
    )

    class Meta:
        model = Camera
        fields = [
            "cross_road",
            "street_address",
            "associated_shop",
            "reported_by",
        ]
        widgets = {
            "cross_road": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "e.g., Canal St & Bourbon St",
            }),
            "street_address": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "e.g., 123 Main St (optional)",
            }),
            "associated_shop": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "e.g., Corner Store (optional)",
            }),
            "reported_by": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "Your email or name (optional)",
            }),
        }

    def clean(self):
        cleaned_data = super().clean()

        # Check honeypot - if filled, it's likely spam
        if cleaned_data.get("website"):
            raise forms.ValidationError("Spam detected.")

        latitude = cleaned_data.get("latitude")
        longitude = cleaned_data.get("longitude")

        if latitude is not None and longitude is not None:
            cleaned_data["location"] = Point(longitude, latitude, srid=4326)
        else:
            raise forms.ValidationError("Please select a location on the map.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.location = self.cleaned_data["location"]
        instance.status = Camera.Status.PENDING
        if commit:
            instance.save()
        return instance


class PhotoProposalForm(forms.ModelForm):
    """Form for proposing a new photo to an existing vetted camera."""

    website = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "autocomplete": "off",
            "tabindex": "-1",
            "style": "position: absolute; left: -9999px;",
        }),
        label="",
    )

    class Meta:
        model = CameraImage
        fields = ["image", "photo_type", "proposed_by"]
        widgets = {
            "image": forms.FileInput(attrs={"accept": "image/*"}),
            "proposed_by": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "Your email or name (optional)",
            }),
        }

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image:
            validate_image_file_size(image)
        return image

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("website"):
            raise forms.ValidationError("Spam detected.")
        return cleaned_data

    def save(self, camera, commit=True):
        instance = super().save(commit=False)
        instance.camera = camera
        instance.status = CameraImage.Status.PENDING
        if commit:
            instance.save()
        return instance
