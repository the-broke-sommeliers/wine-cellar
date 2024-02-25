import random

import factory
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password

from wine_cellar.apps.wine.models import (
    Categories,
    Classification,
    FoodPairing,
    Grape,
    Region,
    Vintage,
    Wine,
)


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()

    username = factory.Sequence(lambda n: "user%d" % n)
    email = factory.Sequence(lambda n: "user%d@wine-cellar.net" % n)
    password = make_password("password")


class RegionFactory(factory.Factory):
    class Meta:
        model = Region

    name = factory.Faker("city")


class GrapeFactory(factory.Factory):
    class Meta:
        model = Grape

    name = factory.Faker("name")


class WineryFactory(factory.Factory):
    class Meta:
        model = Grape

    name = factory.Faker("company")
    region = factory.SubFactory(RegionFactory)


class VintageFactory(factory.Factory):
    class Meta:
        model = Vintage

    name = "1977"


class FoodPairingFactory(factory.Factory):
    class Meta:
        model = FoodPairing

    name = "meat"


class ClassificationFactory(factory.Factory):
    class Meta:
        model = Classification

    name = "Wine"


class WineFactory(factory.Factory):
    class Meta:
        model = Wine

    name = factory.Faker("name")
    wine_type = random.choice(Categories.labels)
    elaborate = "Varietal/100%"
    grapes = factory.SubFactory(GrapeFactory)
    classification = factory.SubFactory(ClassificationFactory)
    food_pairings = factory.RelatedFactoryList(
        FoodPairingFactory, size=random.randint(1, 4)
    )
