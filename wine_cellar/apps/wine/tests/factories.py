import random

import factory
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from factory import post_generation
from factory.django import DjangoModelFactory, ImageField

from wine_cellar.apps.wine.models import (
    Classification,
    FoodPairing,
    Grape,
    Region,
    Vintage,
    Wine,
    WineImage,
    Winery,
    WineType,
)


class UserFactory(DjangoModelFactory):
    class Meta:
        model = get_user_model()

    username = factory.Sequence(lambda n: "user%d" % n)
    email = factory.Sequence(lambda n: "user%d@wine-cellar.net" % n)
    password = make_password("password")


class RegionFactory(DjangoModelFactory):
    class Meta:
        model = Region

    name = factory.Faker("city")


class GrapeFactory(DjangoModelFactory):
    class Meta:
        model = Grape

    name = factory.Faker("name")


class WineryFactory(DjangoModelFactory):
    class Meta:
        model = Winery

    name = factory.Faker("company")
    region = factory.SubFactory(RegionFactory)


class VintageFactory(DjangoModelFactory):
    class Meta:
        model = Vintage

    name = random.randint(1900, 2024)


class FoodPairingFactory(DjangoModelFactory):
    class Meta:
        model = FoodPairing

    name = factory.Faker("name")


class ClassificationFactory(DjangoModelFactory):
    class Meta:
        model = Classification

    name = factory.Faker("name")


class WineFactory(DjangoModelFactory):
    class Meta:
        model = Wine

    user = factory.SubFactory(UserFactory)
    name = factory.Faker("name")
    wine_type = random.choice(WineType.labels)
    elaborate = "Varietal/100%"
    region = factory.SubFactory(RegionFactory)
    winery = factory.SubFactory(WineryFactory)
    # classification = factory.RelatedFactoryList(
    #    ClassificationFactory, size=random.randint(1, 4)
    # )
    # food_pairings = factory.RelatedFactoryList(
    #    FoodPairingFactory, size=random.randint(1, 4)
    # )
    abv = 12.0

    # vintage = factory.RelatedFactoryList(
    #    VintageFactory, size=random.randint(1, 4)
    # )

    @post_generation
    def vintage(obj, create, extracted, **kwargs):
        if not create:
            return
        if not extracted:
            vintage = VintageFactory()
            obj.vintage.add(vintage)
        else:
            obj.save()
            for vintage in extracted:
                obj.vintage.add(vintage)

    @post_generation
    def grapes(obj, create, extracted, **kwargs):
        if not create:
            return
        if not extracted:
            grape = GrapeFactory()
            obj.grapes.add(grape)
        else:
            obj.save()
            for grape in extracted:
                obj.grapes.add(grape)


class WineImageFactory(DjangoModelFactory):
    class Meta:
        model = WineImage

    image = ImageField()
    wine = factory.SubFactory(WineFactory)
    user = factory.SubFactory(UserFactory)
