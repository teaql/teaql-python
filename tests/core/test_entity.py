import pytest
from teaql.core.entity import BaseEntityData, EntityKey, EntityRoot
from teaql.core.value import Value

def test_base_entity_data_creation():
    e = BaseEntityData.new()
    assert e.id == 0
    assert e.version == 0
    assert e.dynamic == {}

    e = e.with_id(10).with_version(2)
    assert e.id == 10
    assert e.version == 2

def test_base_entity_data_dynamic():
    e = BaseEntityData()
    e.with_dynamic("name", "Alice")
    assert "name" in e.dynamic
    assert e.dynamic["name"].val == "Alice"
    
    val = e.get_dynamic("name")
    assert val is not None
    assert val.val == "Alice"
    
    e.put_dynamic("age", Value.I64(30))
    assert e.get_dynamic("age").val == 30

def test_base_entity_data_to_record():
    e = BaseEntityData(id=5, version=1).with_dynamic("name", "Bob")
    rec = e.to_record()
    assert rec == {"id": 5, "version": 1, "name": "Bob"}


def test_entity_root_tracks_final_values_versions_and_lifecycle():
    root = EntityRoot()
    parent = EntityKey("Order", 10)
    child = EntityKey("OrderLine", 20)

    root.set_original_version(parent, 3)
    root.set_original_version(child, 7)
    root.set(parent, "status", "pending")
    root.set(parent, "status", "confirmed")
    root.set(child, "quantity", 2)
    root.mark_as_new(child)

    changes = dict(root.current_change_set().changes())
    assert changes[parent] == {"status": "confirmed"}
    assert changes[child] == {"quantity": 2}
    assert root.original_version(parent) == 3
    assert child in root.new_keys()

    root.mark_as_deleted(child)
    assert child in root.deleted_keys()
    assert child not in dict(root.current_change_set().changes())

    root.clear_committed()
    assert root.current_change_set().is_empty()
    assert root.new_keys() == set()
    assert root.deleted_keys() == set()
