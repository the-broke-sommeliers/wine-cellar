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
    Size,
    Source,
    Vineyard,
    Wine,
    WineImage,
    WineType,
)


class UserFactory(DjangoModelFactory):
    class Meta:
        model = get_user_model()

    username = factory.Sequence(lambda n: "user%d" % n)
    email = factory.Sequence(lambda n: "user%d@wine-cellar.net" % n)
    password = make_password("password")


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


class ClassificationFactory(DjangoModelFactory):
    class Meta:
        model = Classification

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
    wine_type = random.choice(WineType.labels)
    vintage = random.randint(1900, 2024)
    # classification = factory.RelatedFactoryList(
    #    ClassificationFactory, size=random.randint(1, 4)
    # )
    # food_pairings = factory.RelatedFactoryList(
    #    FoodPairingFactory, size=random.randint(1, 4)
    # )
    abv = 12.0

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
