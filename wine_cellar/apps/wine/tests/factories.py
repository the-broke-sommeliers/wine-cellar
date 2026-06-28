import random

import factory
from factory import post_generation
from factory.django import DjangoModelFactory, ImageField

from wine_cellar.apps.user.tests.factories import UserFactory
from wine_cellar.apps.wine.models import (
    Appellation,
    Attribute,
    FoodPairing,
    Grape,
    Region,
    Size,
    Source,
    Vineyard,
    Vintage,
    Wine,
    WineImage,
    WineType,
)


class GrapeFactory(DjangoModelFactory):
    class Meta:
        model = Grape

    name = factory.Faker("name")


class RegionFactory(DjangoModelFactory):
    class Meta:
        model = Region

    name = factory.Faker("name")


class AppellationFactory(DjangoModelFactory):
    class Meta:
        model = Appellation

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

    @post_generation
    def _create_default_vintage(obj, create, extracted, **kwargs):
        if not create:
            return
        if extracted is False:
            return
        if not obj.vintages.exists():
            VintageFactory(wine=obj, user=obj.user)


class VintageFactory(DjangoModelFactory):
    class Meta:
        model = Vintage

    wine = factory.SubFactory(WineFactory, _create_default_vintage=False)
    user = factory.LazyAttribute(lambda v: v.wine.user)
    year = factory.LazyFunction(lambda: random.randint(1900, 2024))
    abv = 12.0


class WineImageFactory(DjangoModelFactory):
    class Meta:
        model = WineImage

    image = ImageField()
    vintage = factory.SubFactory(VintageFactory)
    user = factory.SubFactory(UserFactory)
