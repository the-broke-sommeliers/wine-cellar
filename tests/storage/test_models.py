import pytest

from wine_cellar.apps.storage.models import StorageItem


@pytest.mark.django_db
def test_storage_slots_calcution_correct(
    client, user, wine_factory, storage_factory, storage_item_factory
):
    client.force_login(user)
    storage = storage_factory(user=user, rows=5, columns=5)
    wine = wine_factory(user=user)
    item_deleted = storage_item_factory(
        storage=storage, wine=wine, user=user, row=1, column=1, deleted=True
    )
    item = storage_item_factory(storage=storage, wine=wine, user=user, row=1, column=1)
    item = storage_item_factory(storage=storage, wine=wine, user=user, row=1, column=2)
    assert item.deleted is False
    assert item_deleted.deleted is True
    assert StorageItem.objects.count() == 3
    assert storage.rows == 5
    assert storage.columns == 5
    assert storage.total_slots == 25
    assert storage.used_slots == 2
