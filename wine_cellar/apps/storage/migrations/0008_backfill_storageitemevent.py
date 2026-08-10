"""Best-effort backfill of StorageItemEvent rows for pre-existing
StorageItems. Known limitation: `opened`/`modified` only reflect the
*latest* transition, so an item opened then consumed before this ran gets
no separate historical OPENED timestamp - only the final CONSUMED state."""

from django.db import migrations


def backfill_events(apps, schema_editor):
    StorageItem = apps.get_model("storage", "StorageItem")
    StorageItemEvent = apps.get_model("storage", "StorageItemEvent")

    for item in StorageItem.objects.select_related("wine").iterator():
        wine_name = item.wine.name if item.wine else ""

        added = StorageItemEvent.objects.create(
            storage_item=item,
            wine=item.wine,
            wine_name=wine_name,
            user=item.user,
            event_type="added",
        )
        StorageItemEvent.objects.filter(pk=added.pk).update(created=item.created)

        if item.opened:
            opened = StorageItemEvent.objects.create(
                storage_item=item,
                wine=item.wine,
                wine_name=wine_name,
                user=item.user,
                event_type="opened",
                note=item.opened_note,
            )
            StorageItemEvent.objects.filter(pk=opened.pk).update(
                created=item.modified
            )

        if item.deleted:
            final_type = "consumed" if item.opened else "removed"
            final = StorageItemEvent.objects.create(
                storage_item=item,
                wine=item.wine,
                wine_name=wine_name,
                user=item.user,
                event_type=final_type,
            )
            StorageItemEvent.objects.filter(pk=final.pk).update(
                created=item.modified
            )


class Migration(migrations.Migration):

    dependencies = [
        ("storage", "0007_storageitemevent"),
    ]

    operations = [
        migrations.RunPython(backfill_events, migrations.RunPython.noop),
    ]
