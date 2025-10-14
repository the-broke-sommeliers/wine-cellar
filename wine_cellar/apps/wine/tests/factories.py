import random

import factory
from factory import post_generation
from factory.django import DjangoModelFactory, ImageField

from wine_cellar.apps.user.tests.factories import UserFactory
from wine_cellar.apps.wine.models import (
    Attribute,
    FoodPairing,
    Grape,
    Size,
    Source,
    Vineyard,
    Wine,
    WineImage,
    WineType,
)


class GrapeFactory(DjangoModelFactory):
    class Meta:
        model = Grape

    name = factory.Faker("name")


class SizeFactory(DjangoModelFactory):
    class Meta:
        model = Size

    name = random.randint(0, 100)


class VineyardFactory(DjangoModelFactory):
    class Meta:
        model = Vineyard

    name = factory.Faker("company")


class FoodPairingFactory(DjangoModelFactory):
    class Meta:
        model = FoodPairing

    name = factory.Faker("name")


class AttributeFactory(DjangoModelFactory):
    class Meta:
        model = Attribute

    name = factory.Faker("name")


class SourceFactory(DjangoModelFactory):
    class Meta:
        model = Source

    name = factory.Faker("name")


class WineFactory(DjangoModelFactory):
    class Meta:
        model = Wine

    user = factory.SubFactory(UserFactory)
    name = factory.Faker("name")
    wine_type = random.choice(WineType.choices)[0]
    vintage = random.randint(1900, 2024)
    abv = 12.0
    country = "DE"

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
