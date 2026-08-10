import pytest
from teaql.core.entity import BaseEntityData
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
