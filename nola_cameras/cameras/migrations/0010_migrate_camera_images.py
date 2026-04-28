"""
Data migration: copy existing Camera.image / image_2 / image_3 fields
to CameraImage rows before those columns are dropped.

Mapping:
  image   → close_up
  image_2 → surrounding
  image_3 → project_nola_sign

Status:
  vetted cameras  → approved
  everything else → pending
"""

import uuid

from django.db import migrations


def migrate_images_forward(apps, schema_editor):
    Camera = apps.get_model("cameras", "Camera")
    CameraImage = apps.get_model("cameras", "CameraImage")

    type_map = [
        ("image",   "close_up"),
        ("image_2", "surrounding"),
        ("image_3", "project_nola_sign"),
    ]

    for camera in Camera.objects.all():
        for field_name, photo_type in type_map:
            val = getattr(camera, field_name, None)
            if val:
                status = "approved" if camera.status == "vetted" else "pending"
                CameraImage.objects.create(
                    id=uuid.uuid4(),
                    camera=camera,
                    image=val,
                    photo_type=photo_type,
                    status=status,
                    proposed_by=camera.reported_by or "",
                    proposed_at=camera.reported_at,
                )


def migrate_images_backward(apps, schema_editor):
    Camera = apps.get_model("cameras", "Camera")
    CameraImage = apps.get_model("cameras", "CameraImage")

    type_to_field = {
        "close_up":          "image",
        "surrounding":       "image_2",
        "project_nola_sign": "image_3",
    }

    for img in CameraImage.objects.select_related("camera"):
        field_name = type_to_field.get(img.photo_type)
        if field_name:
            setattr(img.camera, field_name, img.image)
            img.camera.save(update_fields=[field_name])


class Migration(migrations.Migration):

    dependencies = [
        ("cameras", "0009_add_cameraimage_model"),
    ]

    operations = [
        migrations.RunPython(migrate_images_forward, migrate_images_backward),
    ]
