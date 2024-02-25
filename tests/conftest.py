from pytest_factoryboy import register

from wine_cellar.apps.wine.tests.factories import (
    RegionFactory,
    UserFactory,
    WineFactory,
)

register(UserFactory)
register(RegionFactory)
register(WineFactory)
