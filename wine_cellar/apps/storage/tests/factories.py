import random

import factory
from factory.django import DjangoModelFactory

from wine_cellar.apps.storage.models import (
    Storage,
    StorageItem,
    StorageItemEvent,
    StorageItemEventType,
    StorageLabel,
)
from wine_cellar.apps.user.tests.factories import UserFactory
from wine_cellar.apps.wine.tests.factories import VintageFactory


class StorageFactory(DjangoModelFactory):
    class Meta:
        model = Storage

    name = factory.Faker("name")
    location = factory.Faker("address")
    rows = random.randint(1, 10)
    columns = random.randint(1, 10)
    user = factory.SubFactory(UserFactory)


class StorageItemFactory(DjangoModelFactory):
    class Meta:
        model = StorageItem

    storage = factory.SubFactory(StorageFactory)
    vintage = factory.SubFactory(VintageFactory)


class StorageItemEventFactory(DjangoModelFactory):
    class Meta:
        model = StorageItemEvent

    storage_item = factory.SubFactory(StorageItemFactory)
    vintage = factory.LazyAttribute(
        lambda o: o.storage_item.vintage if o.storage_item else None
    )
    wine = factory.LazyAttribute(lambda o: o.vintage.wine if o.vintage else None)
    wine_name = factory.LazyAttribute(lambda o: o.wine.name if o.wine else "")
    vintage_year = factory.LazyAttribute(
        lambda o: o.vintage.year if o.vintage else None
    )
    event_type = StorageItemEventType.ADDED
    user = factory.SubFactory(UserFactory)


class StorageLabelFactory(DjangoModelFactory):
    class Meta:
        model = StorageLabel

    storage = factory.SubFactory(StorageFactory)
    axis = "row"
    index = 1
    name = factory.Faker("word")
    user = factory.SubFactory(UserFactory)
