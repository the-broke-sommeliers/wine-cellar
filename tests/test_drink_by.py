from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone

from wine_cellar.apps.storage.models import StorageItem
from wine_cellar.apps.user.views import get_user_settings
from wine_cellar.apps.wine.models import Wine
from wine_cellar.apps.wine.tasks import drink_by_reminder, opened_bottle_reminder


@pytest.mark.django_db
def test_drink_by_reminder(user, wine_factory):
    date = timezone.now().date() + timedelta(days=14)
    wine = wine_factory(drink_by=date, user=user)
    wine_1 = wine_factory(drink_by=timezone.now().date(), user=user)
    storage = user.storage_set.first()
    StorageItem.objects.create(wine=wine, storage=storage)
    StorageItem.objects.create(wine=wine_1, storage=storage)
    drink_by_reminder()
    assert Wine.objects.count() == 2
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_drink_by_reminder_not_send_if_notifications_disabled(user, wine_factory):
    user_settings = get_user_settings(user)
    user_settings.notifications = False
    user_settings.save()
    date = timezone.now().date() + timedelta(days=14)
    wine = wine_factory(drink_by=date, user=user)
    wine_1 = wine_factory(drink_by=timezone.now().date(), user=user)
    storage = user.storage_set.first()
    StorageItem.objects.create(wine=wine, storage=storage)
    StorageItem.objects.create(wine=wine_1, storage=storage)
    drink_by_reminder()
    assert Wine.objects.count() == 2
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_drink_by_reminder_not_send_for_other_user(user, user_factory, wine_factory):
    date = timezone.now().date() + timedelta(days=14)
    user1 = user_factory(email="user1@example.org")
    wine = wine_factory(drink_by=date, user=user1)
    wine_1 = wine_factory(drink_by=timezone.now().date(), user=user)
    storage = user.storage_set.first()
    storage_1 = user1.storage_set.first()
    StorageItem.objects.create(wine=wine, storage=storage_1)
    StorageItem.objects.create(wine=wine_1, storage=storage)
    drink_by_reminder()
    assert Wine.objects.count() == 2
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [user1.email]


@pytest.mark.django_db
def test_drink_by_reminder_not_sent_without_stock(user, wine_factory):
    date = timezone.now().date() + timedelta(days=14)
    wine_factory(drink_by=date, user=user)
    drink_by_reminder()
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_drink_by_reminder_email_subject(user, wine_factory):
    date = timezone.now().date() + timedelta(days=14)
    wine = wine_factory(drink_by=date, user=user)
    storage = user.storage_set.first()
    StorageItem.objects.create(wine=wine, storage=storage)
    drink_by_reminder()
    assert len(mail.outbox) == 1
    assert "Reminder" in mail.outbox[0].subject


@pytest.mark.django_db
def test_opened_bottle_reminder(user, wine_factory, storage_item_factory):
    today = timezone.now().date()
    wine = wine_factory(user=user)
    storage = user.storage_set.first()
    storage_item_factory(
        wine=wine,
        storage=storage,
        user=user,
        opened=True,
        deleted=False,
        drink_by=today,
    )
    opened_bottle_reminder()
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_opened_bottle_reminder_not_sent_if_notifications_disabled(
    user, wine_factory, storage_item_factory
):
    user_settings = get_user_settings(user)
    user_settings.notifications = False
    user_settings.save()
    today = timezone.now().date()
    wine = wine_factory(user=user)
    storage = user.storage_set.first()
    storage_item_factory(
        wine=wine,
        storage=storage,
        user=user,
        opened=True,
        deleted=False,
        drink_by=today,
    )
    opened_bottle_reminder()
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_opened_bottle_reminder_not_sent_for_deleted_item(
    user, wine_factory, storage_item_factory
):
    today = timezone.now().date()
    wine = wine_factory(user=user)
    storage = user.storage_set.first()
    storage_item_factory(
        wine=wine, storage=storage, user=user, opened=True, deleted=True, drink_by=today
    )
    opened_bottle_reminder()
    assert len(mail.outbox) == 0
