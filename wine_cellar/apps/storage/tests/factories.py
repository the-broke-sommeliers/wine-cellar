import random

import factory
from factory.django import DjangoModelFactory

from wine_cellar.apps.storage.models import Storage
from wine_cellar.apps.user.tests.factories import UserFactory


class StorageFactory(DjangoModelFactory):
    class Meta:
        model = Storage

    name = factory.Faker("name")
    location = factory.Faker("address")
    rows = random.randint(1, 10)
    columns = random.randint(1, 10)
    user = factory.SubFactory(UserFactory)
