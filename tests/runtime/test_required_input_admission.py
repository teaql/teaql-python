"""Pure admission before generated stable-ID reservation; never replaces Check/Fix."""
import pytest

from teaql.core.meta import EntityDescriptor, PropertyDescriptor, RelationDescriptor
from teaql.core.mutation import DeleteCommand, InsertCommand, UpdateCommand
from teaql.runtime import CheckException, RuntimeModule, UserContext


def context():
    schema = (EntityDescriptor("Probe")
        .property(PropertyDescriptor("id").required().is_id())
        .property(PropertyDescriptor("version").required().is_version())
        .property(PropertyDescriptor("required_string").required())
        .property(PropertyDescriptor("required_quantity").required())
        .property(PropertyDescriptor("active").required())
        .property(PropertyDescriptor("parent_object").required())
        .property(PropertyDescriptor("create_time").required().fixed_by_runtime(insert=True))
        .property(PropertyDescriptor("update_time").required().fixed_by_runtime(insert=True, update=True))
        .property(PropertyDescriptor("order_number").required().fixed_by_runtime(insert=True))
        .relation(RelationDescriptor("parent_object", "Parent").local("parent_object").foreign("id")))
    ctx = RuntimeModule().schema_entity(schema).into_context()
    class NoProvider:
        # Protocol/attribute discovery during resource installation is not I/O.
        # Fail on calls to the actual provider boundary, not on hasattr().
        async def begin(self, *_):
            raise AssertionError("required input admission began a transaction")
        async def next_id(self, *_):
            raise AssertionError("required input admission reserved an ID")
        async def mutate(self, *_):
            raise AssertionError("required input admission executed a mutation")
        async def query(self, *_):
            raise AssertionError("required input admission executed a query")
    ctx.insert_resource("dataService", NoProvider())
    return ctx


def valid_input():
    return (InsertCommand.new("Probe").value("required_string", "ready")
        .value("required_quantity", 0).value("active", False).value("parent_object", 1))


@pytest.mark.parametrize("field", ["required_string", "required_quantity", "active", "parent_object"])
@pytest.mark.parametrize("operation", ["insert", "update"])
def test_missing_required_input_uses_canonical_paths_without_io(field, operation):
    ctx = context()
    mutation = valid_input() if operation == "insert" else UpdateCommand.new("Probe", 1)
    mutation.value(field, None)
    with pytest.raises(CheckException) as error:
        ctx._validate_required_mutation_input(mutation)
    assert [v.location.model_path for v in error.value.violations] == [field]
    assert error.value.violations[0].location.instance_path.startswith("/")
    assert error.value.violations[0].entity_type == "Probe"
    assert error.value.violations[0].to_wire()["entityType"] == "Probe"
    assert ctx.get_resource("fix_time") is None
    assert ctx.last_fix_evidence() == ()


def test_create_defaults_and_known_cascade_parent_are_not_fabricated():
    ctx = context()
    mutation = valid_input()
    mutation.values.pop("parent_object")
    before = dict(mutation.values)
    ctx._validate_required_mutation_input(mutation, parent_field="parent_object")
    assert mutation.values == before
    assert "id" not in mutation.values
    assert "create_time" not in mutation.values
    # Outside an actual generated parent cascade the association is required.
    with pytest.raises(CheckException) as error:
        ctx._validate_required_mutation_input(mutation)
    assert error.value.violations[0].location.model_path == "parent_object"


def test_admission_is_not_full_update_or_delete_validation():
    ctx = context()
    update = UpdateCommand.new("Probe", 1).value("update_time", None)
    ctx._validate_required_mutation_input(update)
    ctx._validate_required_mutation_input(DeleteCommand("Probe", 1))
    # Create-only defaults are not a license to erase persisted business data.
    with pytest.raises(CheckException):
        ctx._validate_required_mutation_input(UpdateCommand.new("Probe", 1).value("create_time", None))
