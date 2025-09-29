import factory
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from factory.django import DjangoModelFactory


class UserFactory(DjangoModelFactory):
    class Meta:
        model = get_user_model()

    username = factory.Sequence(lambda n: "user%d" % n)
    email = factory.Sequence(lambda n: "user%d@wine-cellar.net" % n)
    password = make_password("password")
