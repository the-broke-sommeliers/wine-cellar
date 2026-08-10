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
from wine_cellar.apps.wine.tests.factories import WineFactory


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
    wine = factory.SubFactory(WineFactory)


class StorageItemEventFactory(DjangoModelFactory):
    class Meta:
        model = StorageItemEvent

    storage_item = factory.SubFactory(StorageItemFactory)
    wine = factory.LazyAttribute(
        lambda o: o.storage_item.wine if o.storage_item else None
    )
    wine_name = factory.LazyAttribute(lambda o: o.wine.name if o.wine else "")
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
