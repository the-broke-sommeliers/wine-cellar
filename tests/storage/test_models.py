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


@pytest.mark.django_db
def test_is_full_true(user, wine_factory, storage_factory, storage_item_factory):
    storage = storage_factory(user=user, rows=1, columns=1)
    wine = wine_factory(user=user)
    storage_item_factory(storage=storage, wine=wine, row=1, column=1)
    assert storage.is_full is True


@pytest.mark.django_db
def test_is_full_false(user, wine_factory, storage_factory, storage_item_factory):
    storage = storage_factory(user=user, rows=2, columns=2)
    wine = wine_factory(user=user)
    storage_item_factory(storage=storage, wine=wine, row=1, column=1)
    assert storage.is_full is False


@pytest.mark.django_db
def test_is_slot_occupied_true(
    user, wine_factory, storage_factory, storage_item_factory
):
    storage = storage_factory(user=user, rows=2, columns=2)
    wine = wine_factory(user=user)
    storage_item_factory(storage=storage, wine=wine, row=1, column=1)
    assert storage.is_slot_occupied(1, 1) is True


@pytest.mark.django_db
def test_is_slot_occupied_false_after_delete(
    user, wine_factory, storage_factory, storage_item_factory
):
    storage = storage_factory(user=user, rows=2, columns=2)
    wine = wine_factory(user=user)
    storage_item_factory(storage=storage, wine=wine, row=1, column=1, deleted=True)
    assert storage.is_slot_occupied(1, 1) is False


@pytest.mark.django_db
def test_get_wines_excludes_deleted(
    user, wine_factory, storage_factory, storage_item_factory
):
    storage = storage_factory(user=user, rows=2, columns=2)
    wine = wine_factory(user=user)
    active_item = storage_item_factory(storage=storage, wine=wine, row=1, column=1)
    storage_item_factory(storage=storage, wine=wine, row=1, column=2, deleted=True)
    wines = list(storage.get_wines)
    assert len(wines) == 1
    assert wines[0] == active_item


@pytest.mark.django_db
def test_row_labels(user, storage_factory, storage_label_factory):
    storage = storage_factory(user=user, rows=3, columns=3)
    storage_label_factory(storage=storage, axis="row", index=1, name="Spain")
    storage_label_factory(storage=storage, axis="row", index=3, name="Italy")
    storage_label_factory(storage=storage, axis="column", index=1, name="Reds")
    assert storage.row_labels == {1: "Spain", 3: "Italy"}


@pytest.mark.django_db
def test_column_labels(user, storage_factory, storage_label_factory):
    storage = storage_factory(user=user, rows=3, columns=3)
    storage_label_factory(storage=storage, axis="column", index=2, name="Cheap")
    storage_label_factory(storage=storage, axis="row", index=1, name="Spain")
    assert storage.column_labels == {2: "Cheap"}


@pytest.mark.django_db
def test_labels_empty_by_default(user, storage_factory):
    storage = storage_factory(user=user, rows=2, columns=2)
    assert storage.row_labels == {}
    assert storage.column_labels == {}
