"""Add StorageItemEvent.vintage (+ vintage_year snapshot, mirroring the
existing wine_name snapshot) and backfill both from each event's
storage_item, now that StorageItem points at Vintage."""

import django.db.models.deletion
from django.db import migrations, models


def backfill_vintage(apps, schema_editor):
    # Events whose storage_item was already hard-deleted before this
    # migration ran (storage_item_id is SET_NULL'd on delete) keep
    # vintage/vintage_year as None - there's no vintage left to recover for
    # them, they still carry the wine_name snapshot. Accepted gap, not a bug.
    StorageItemEvent = apps.get_model("storage", "StorageItemEvent")

    events = StorageItemEvent.objects.filter(
        storage_item__isnull=False, storage_item__vintage__isnull=False
    ).select_related("storage_item__vintage")
    for event in events.iterator():
        vintage = event.storage_item.vintage
        event.vintage = vintage
        event.vintage_year = vintage.year
        event.save(update_fields=["vintage", "vintage_year"])


class Migration(migrations.Migration):

    dependencies = [
        ("storage", "0011_cleanup_storage_item"),
        ("wine", "0020_migrate_vintage_data"),
    ]

    operations = [
        migrations.AddField(
            model_name="storageitemevent",
            name="vintage",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="events",
                to="wine.vintage",
            ),
        ),
        migrations.AddField(
            model_name="storageitemevent",
            name="vintage_year",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.RunPython(backfill_vintage, migrations.RunPython.noop),
    ]
