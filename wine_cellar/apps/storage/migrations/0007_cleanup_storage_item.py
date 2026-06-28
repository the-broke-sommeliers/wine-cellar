import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("storage", "0006_add_vintage_fk"),
        ("wine", "0020_migrate_vintage_data"),
    ]

    operations = [
        migrations.AlterField(
            model_name="storageitem",
            name="vintage",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="wine.vintage",
            ),
        ),
        migrations.RemoveField(model_name="storageitem", name="wine"),
    ]
