"""Small Context Fix regressions, independent of the large domain fixtures."""
import pytest

from teaql.core.entity import EntityKey, EntityRoot
from teaql.core.meta import EntityDescriptor, PropertyDescriptor
from teaql.core.mutation import InsertCommand
from teaql.core.value import DataType, Value
from teaql.runtime import CheckException, CheckResult, ObjectLocation, RuntimeModule


class Probe:
    def __init__(self, identity, name):
        self.id, self.name, self._action = identity, name, "Create"
        self._entity_root = EntityRoot()
        self._entity_root.mark_as_new(self._teaql_entity_key())
        self._entity_root.set(self._teaql_entity_key(), "name", Value.Text(name))

    def _teaql_entity_key(self):
        return EntityKey("Probe", self.id)

    def _teaql_scalar_payload(self):
        return {"id": Value.I64(self.id), "name": Value.Text(self.name)}

    def _teaql_graph_relations(self):
        return {}


def fixture():
    class Checker:
        def check_and_fix(self, context, record, location, results):
            record["source_ip"] = Value.Text("B:source_ip")
            if record["name"].val == "INVALID":
                results.append(CheckResult("required", ObjectLocation().property("name")))

    class NoProvider:
        async def begin(self, context):
            pytest.fail("invalid preparation reached the provider")

    source_ip = PropertyDescriptor("source_ip")
    # Declarative ownership under a non-clock name. The baseline accepts but
    # does not yet consume this metadata; no new API is needed to reproduce it.
    source_ip.create_function = "identity"
    descriptor = (EntityDescriptor("Probe")
                  .property(PropertyDescriptor("id", DataType.I64).is_id())
                  .property(PropertyDescriptor("name").required())
                  .property(source_ip))
    return (RuntimeModule().entity(Probe).schema_entity(descriptor)
            .checker("Probe", Checker()).into_context()
            .insert_resource("dataService", NoProvider()))


@pytest.mark.asyncio
async def test_rejected_entity_does_not_publish_staged_context_to_ledger():
    context, entity = fixture(), Probe(1, "INVALID")

    async def prepare(session):
        session._generated.fix(entity, "Create", InsertCommand("Probe", entity._teaql_scalar_payload()))

    async def work(session):
        pytest.fail("invalid preparation reached work")

    with pytest.raises(CheckException) as error:
        await context.execute_graph_save(work, prepare=prepare, comment="reject automatic Context staging")
    assert error.value.violations[0].location.instance_path == "/name"
    assert error.value.violations[0].entity_type == "Probe"
    changes = dict(entity._entity_root.current_change_set().changes())[entity._teaql_entity_key()]
    assert changes == {"name": Value.Text("INVALID")}
    assert context.get_resource("fix_time") is None


@pytest.mark.asyncio
async def test_later_invalid_entity_discards_earlier_context_fix_but_keeps_caller_intent():
    context = fixture()
    first, second = Probe(1, "caller edit"), Probe(2, "INVALID")

    async def prepare(session):
        for entity in (first, second):
            session._generated.fix(entity, "Create", InsertCommand("Probe", entity._teaql_scalar_payload()))

    async def work(session):
        pytest.fail("invalid preparation reached work")

    with pytest.raises(CheckException):
        await context.execute_graph_save(work, prepare=prepare, comment="unwind successful sibling Context Fix")
    for entity in (first, second):
        changes = dict(entity._entity_root.current_change_set().changes())[entity._teaql_entity_key()]
        assert changes == {"name": Value.Text(entity.name)}
    assert context.get_resource("fix_time") is None
