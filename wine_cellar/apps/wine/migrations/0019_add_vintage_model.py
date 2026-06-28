import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("wine", "0018_remove_django_celery_beat"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Vintage",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("modified", models.DateTimeField(auto_now=True)),
                (
                    "year",
                    models.PositiveIntegerField(
                        blank=True,
                        null=True,
                        validators=[django.core.validators.MinValueValidator(1900)],
                    ),
                ),
                ("abv", models.FloatField(blank=True, null=True)),
                (
                    "barcode",
                    models.CharField(blank=True, max_length=100, null=True),
                ),
                (
                    "price",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=6, null=True
                    ),
                ),
                ("drink_by", models.DateField(blank=True, null=True)),
                ("comment", models.CharField(blank=True, max_length=250)),
                (
                    "rating",
                    models.PositiveIntegerField(
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(10),
                        ],
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "wine",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="vintages",
                        to="wine.wine",
                    ),
                ),
            ],
            options={"abstract": False},
        ),
        migrations.AddConstraint(
            model_name="vintage",
            constraint=models.UniqueConstraint(
                fields=["wine", "year", "user"], name="unique vintage"
            ),
        ),
        migrations.AddField(
            model_name="wineimage",
            name="vintage",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="wine.vintage",
            ),
        ),
    ]
