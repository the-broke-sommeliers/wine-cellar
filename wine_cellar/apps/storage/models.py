from django.db import models

from wine_cellar.apps.wine.models import UserContentModel, Wine


class Storage(UserContentModel):
    name = models.CharField(max_length=100, verbose_name="Storage Name")
    description = models.TextField(
        verbose_name="Storage Description", null=True, blank=True
    )
    location = models.CharField(max_length=100, verbose_name="Location")
    rows = models.PositiveIntegerField(default=0, verbose_name="Number of Rows")
    columns = models.PositiveIntegerField(default=0, verbose_name="Number of Columns")

    def __str__(self):
        return self.name

    @property
    def total_slots(self):
        return self.rows * self.columns

    @property
    def used_slots(self):
        return self.items.count()

    @property
    def is_full(self):
        return self.used_slots >= self.total_slots

    def is_slot_occupied(self, row, column):
        return self.items.filter(row=row, column=column, deleted=False).exists()

    @property
    def get_wines(self):
        return self.items.filter(deleted=False).order_by("row", "column")


class StorageItem(UserContentModel):
    storage = models.ForeignKey(Storage, on_delete=models.CASCADE, related_name="items")
    wine = models.ForeignKey(Wine, on_delete=models.CASCADE)
    row = models.PositiveIntegerField(null=True, blank=True)
    column = models.PositiveIntegerField(null=True, blank=True)
    deleted = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=6, decimal_places=2, null=True)
