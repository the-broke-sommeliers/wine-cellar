import random

import factory

from wine_cellar.apps.wine.models import (
    Categories,
    Classification,
    FoodPairing,
    Grape,
    Region,
    Vintage,
    Wine,
)


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
