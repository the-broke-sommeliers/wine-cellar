from django.db import models
from django.utils.translation import gettext_lazy as _

from wine_cellar.apps.wine.models import UserContentModel, Wine


class StorageLabelAxis(models.TextChoices):
    ROW = "row", _("Row")
    COLUMN = "column", _("Column")


class Storage(UserContentModel):
    name = models.CharField(max_length=100, verbose_name="Storage Name")
    description = models.TextField(
        verbose_name="Storage Description", null=True, blank=True
    )
    location = models.CharField(max_length=100, verbose_name="Location")
    rows = models.PositiveIntegerField(default=0, verbose_name="Number of Rows")
    columns = models.PositiveIntegerField(default=0, verbose_name="Number of Columns")
    swap_axes = models.BooleanField(default=False, verbose_name="Show Columns First")
    row_labels_enabled = models.BooleanField(
        default=True, verbose_name="Show Row Labels"
    )
    column_labels_enabled = models.BooleanField(
        default=True, verbose_name="Show Column Labels"
    )

    def __str__(self):
        return self.name

    @property
    def total_slots(self):
        return self.rows * self.columns

    @property
    def used_slots(self):
        return self.items.filter(deleted=False).count()

    @property
    def is_full(self):
        return self.used_slots >= self.total_slots

    def is_slot_occupied(self, row, column):
        return self.items.filter(row=row, column=column, deleted=False).exists()

    @property
    def get_wines(self):
        return self.items.filter(deleted=False).order_by("row", "column")

    def _labels(self, axis):
        return {label.index: label.name for label in self.labels.filter(axis=axis)}

    @property
    def row_labels(self):
        return self._labels(StorageLabelAxis.ROW)

    @property
    def column_labels(self):
        return self._labels(StorageLabelAxis.COLUMN)


class StorageItem(UserContentModel):
    storage = models.ForeignKey(Storage, on_delete=models.CASCADE, related_name="items")
    wine = models.ForeignKey(Wine, on_delete=models.CASCADE)
    row = models.PositiveIntegerField(null=True, blank=True)
    column = models.PositiveIntegerField(null=True, blank=True)
    deleted = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=6, decimal_places=2, null=True)
    opened = models.BooleanField(default=False)
    opened_note = models.TextField(blank=True, null=True)
    drink_by = models.DateField(blank=True, null=True)


class StorageLabel(UserContentModel):
    storage = models.ForeignKey(
        Storage, on_delete=models.CASCADE, related_name="labels"
    )
    axis = models.CharField(max_length=6, choices=StorageLabelAxis.choices)
    index = models.PositiveIntegerField()
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ("storage", "axis", "index")

    def __str__(self):
        return f"{self.storage.name} {self.axis} {self.index}: {self.name}"
