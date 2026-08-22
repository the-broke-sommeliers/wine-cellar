import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("storage", "0009_storageitem_unique_active_slot_per_storage"),
        ("wine", "0019_add_vintage_model"),
    ]

    operations = [
        migrations.AddField(
            model_name="storageitem",
            name="vintage",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="wine.vintage",
            ),
        ),
    ]
