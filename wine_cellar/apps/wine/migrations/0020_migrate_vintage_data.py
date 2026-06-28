from django.db import migrations


def migrate_vintages(apps, schema_editor):
    Wine = apps.get_model("wine", "Wine")
    Vintage = apps.get_model("wine", "Vintage")
    WineImage = apps.get_model("wine", "WineImage")
    StorageItem = apps.get_model("storage", "StorageItem")

    for wine in Wine.objects.all():
        vintage = Vintage.objects.create(
            wine=wine,
            user=wine.user,
            year=wine.vintage,
            abv=wine.abv,
            barcode=wine.barcode,
            price=wine.price,
            drink_by=wine.drink_by,
            rating=wine.rating,
            comment=wine.comment,
        )
        WineImage.objects.filter(wine=wine).update(vintage=vintage)
        StorageItem.objects.filter(wine=wine).update(vintage=vintage)


def reverse_migrate_vintages(apps, schema_editor):
    Wine = apps.get_model("wine", "Wine")
    Vintage = apps.get_model("wine", "Vintage")
    WineImage = apps.get_model("wine", "WineImage")
    StorageItem = apps.get_model("storage", "StorageItem")

    for vintage in Vintage.objects.select_related("wine").all():
        wine = vintage.wine
        wine.vintage = vintage.year
        wine.abv = vintage.abv
        wine.barcode = vintage.barcode
        wine.price = vintage.price
        wine.drink_by = vintage.drink_by
        wine.rating = vintage.rating
        wine.comment = vintage.comment
        wine.save()
        WineImage.objects.filter(vintage=vintage).update(wine=wine)
        StorageItem.objects.filter(vintage=vintage).update(wine=wine)
    Vintage.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("wine", "0019_add_vintage_model"),
        ("storage", "0006_add_vintage_fk"),
    ]

    operations = [
        migrations.RunPython(migrate_vintages, reverse_migrate_vintages),
    ]
