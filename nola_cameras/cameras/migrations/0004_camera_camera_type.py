from django.db import migrations, models


def set_existing_to_project_nola(apps, schema_editor):
    Camera = apps.get_model("cameras", "Camera")
    Camera.objects.all().update(camera_type="project_nola")


class Migration(migrations.Migration):

    dependencies = [
        ("cameras", "0003_make_cross_road_optional"),
    ]

    operations = [
        migrations.AddField(
            model_name="camera",
            name="camera_type",
            field=models.CharField(
                choices=[
                    ("project_nola", "Project NOLA"),
                    ("nopd", "NOPD"),
                    ("private", "Private"),
                    ("unknown", "Unknown"),
                ],
                db_index=True,
                default="unknown",
                max_length=20,
            ),
        ),
        migrations.RunPython(
            set_existing_to_project_nola,
            migrations.RunPython.noop,
        ),
    ]
