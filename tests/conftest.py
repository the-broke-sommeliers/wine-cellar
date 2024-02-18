from pytest_factoryboy import register

from wine_cellar.apps.wine.tests.factories import RegionFactory, WineFactory

register(RegionFactory)
register(WineFactory)
