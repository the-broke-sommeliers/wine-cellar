# Custom migration which adds the most common sizes to the database

from django.db import migrations

sizes = [0.1875, 0.375, 0.5, 0.75, 1.0, 1.5, 3.0, 4.5]


def add_sizes(apps, schema_editor):
    Size = apps.get_model("wine", "Size")
    for s in sizes:
        Size.objects.get_or_create(name=s)


class Migration(migrations.Migration):
    dependencies = [
        ("wine", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(add_sizes, migrations.RunPython.noop),
    ]
