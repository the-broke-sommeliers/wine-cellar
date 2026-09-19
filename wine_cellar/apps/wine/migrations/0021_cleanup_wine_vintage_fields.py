from collections import defaultdict

import django.db.models.deletion
from django.db import migrations, models

NAME_MAX_LENGTH = 100


def rename_duplicate_wines(apps, schema_editor):
    """0020 leaves year-colliding or dissimilar wines as standalone rows that
    still share the new unique key. Suffix the newer ones with " (n)" so the
    constraint below can be added."""
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute("SET CONSTRAINTS ALL IMMEDIATE")

    Wine = apps.get_model("wine", "Wine")
    rows = [
        (pk, name, (wine_type, size_id, country, user_id))
        for pk, name, wine_type, size_id, country, user_id in Wine.objects.order_by(
            "pk"
        ).values_list("pk", "name", "wine_type", "size_id", "country", "user_id")
    ]
    taken = defaultdict(set)
    for _pk, name, key in rows:
        taken[key].add(name)

    claimed = defaultdict(set)
    for pk, name, key in rows:
        # NULLs are distinct in a unique constraint, so these can't collide
        if key[1] is None or key[3] is None or name not in claimed[key]:
            claimed[key].add(name)
            continue
        n = 2
        while True:
            suffix = f" ({n})"
            candidate = name[: NAME_MAX_LENGTH - len(suffix)] + suffix
            if candidate not in taken[key]:
                break
            n += 1
        taken[key].add(candidate)
        claimed[key].add(candidate)
        Wine.objects.filter(pk=pk).update(name=candidate)


class Migration(migrations.Migration):

    dependencies = [
        ("wine", "0020_migrate_vintage_data"),
        ("storage", "0012_storageitemevent_vintage"),
    ]

    operations = [
        migrations.RunPython(rename_duplicate_wines, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name="wine",
            name="unique wine",
        ),
        migrations.RemoveField(model_name="wine", name="vintage"),
        migrations.RemoveField(model_name="wine", name="abv"),
        migrations.RemoveField(model_name="wine", name="barcode"),
        migrations.RemoveField(model_name="wine", name="price"),
        migrations.RemoveField(model_name="wine", name="drink_by"),
        migrations.RemoveField(model_name="wine", name="rating"),
        migrations.RemoveField(model_name="wine", name="comment"),
        migrations.AddConstraint(
            model_name="wine",
            constraint=models.UniqueConstraint(
                fields=("name", "wine_type", "size", "country", "user"),
                name="unique wine",
            ),
        ),
        migrations.AlterField(
            model_name="wineimage",
            name="vintage",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="wine.vintage",
            ),
        ),
        migrations.RemoveField(
            model_name="wineimage",
            name="wine",
        ),
    ]
