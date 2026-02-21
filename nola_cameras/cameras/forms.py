"""
Forms for camera submission.
"""

from django import forms
from django.contrib.gis.geos import Point

from .models import Camera


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

    # Latitude and longitude fields for map picker
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

    class Meta:
        model = Camera
        fields = [
            "cross_road",
            "street_address",
            "facial_recognition",
            "associated_shop",
            "reported_by",
            "image",
            "image_2",
            "image_3",
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
            "facial_recognition": forms.CheckboxInput(attrs={
                "class": "form-checkbox",
            }),
            "image": forms.FileInput(attrs={
                "class": "form-file",
                "accept": "image/*",
            }),
            "image_2": forms.FileInput(attrs={
                "class": "form-file",
                "accept": "image/*",
            }),
            "image_3": forms.FileInput(attrs={
                "class": "form-file",
                "accept": "image/*",
            }),
        }

    def clean(self):
        cleaned_data = super().clean()

        # Check honeypot - if filled, it's likely spam
        if cleaned_data.get("website"):
            raise forms.ValidationError("Spam detected.")

        # Create Point from lat/lng
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
