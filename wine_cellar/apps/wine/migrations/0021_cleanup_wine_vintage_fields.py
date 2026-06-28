import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("wine", "0020_migrate_vintage_data"),
    ]

    operations = [
        # Remove the old unique constraint first (it includes vintage and abv)
        migrations.RemoveConstraint(model_name="wine", name="unique wine"),
        # Remove vintage-level fields from Wine
        migrations.RemoveField(model_name="wine", name="vintage"),
        migrations.RemoveField(model_name="wine", name="abv"),
        migrations.RemoveField(model_name="wine", name="barcode"),
        migrations.RemoveField(model_name="wine", name="price"),
        migrations.RemoveField(model_name="wine", name="drink_by"),
        migrations.RemoveField(model_name="wine", name="rating"),
        migrations.RemoveField(model_name="wine", name="comment"),
        # Add the new smaller unique constraint
        migrations.AddConstraint(
            model_name="wine",
            constraint=models.UniqueConstraint(
                fields=["name", "wine_type", "size", "country", "user"],
                name="unique wine",
            ),
        ),
        # Make WineImage.vintage non-nullable and remove old wine FK
        migrations.AlterField(
            model_name="wineimage",
            name="vintage",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="wine.vintage",
            ),
        ),
        migrations.RemoveField(model_name="wineimage", name="wine"),
    ]
