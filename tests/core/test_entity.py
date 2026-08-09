from teaql.core.entity import BaseEntityData
from teaql.core.value import Value

def test_base_entity_data():
    entity = BaseEntityData.new().with_id(123).with_version(2).with_dynamic("name", "Alice")
    assert entity.id == 123
    assert entity.version == 2
    assert entity.get_dynamic("name") == Value.Text("Alice")
    assert entity.get_dynamic("missing") is None
