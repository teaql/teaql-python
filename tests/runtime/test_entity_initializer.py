import pytest

from teaql.runtime import UserContext


def test_initialize_entity_uses_optional_trusted_initializer():
    context = UserContext()
    entity = {}
    assert context.initialize_entity("Person", entity) is entity

    calls = []
    context.register_entity_initializer("*", lambda current, value: calls.append(("*", current, value)))
    context.register_entity_initializer("Person", lambda current, value: calls.append(("Person", current, value)))
    second = {}
    assert context.initialize_entity("Person", second) is second
    assert calls == [("*", context, second), ("Person", context, second)]
    assert context.managed_entities() == [entity, second]


def test_initialize_entity_rejects_invalid_contracts():
    context = UserContext()
    with pytest.raises(ValueError):
        context.initialize_entity(" ", {})
    with pytest.raises(ValueError):
        context.initialize_entity("Person", None)


def test_user_context_does_not_own_a_mutation_ledger():
    context = UserContext.new()
    assert not hasattr(context, "entity_root")

    with pytest.raises(ValueError):
        context.register_entity_initializer("Person", object())
