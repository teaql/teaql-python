import pytest

from teaql.runtime import UserContext


def test_initialize_entity_uses_optional_trusted_initializer():
    ctx = UserContext()
    entity = {}
    assert ctx.initialize_entity("Person", entity) is entity

    calls = []
    ctx.register_entity_initializer("*", lambda current, value: calls.append(("*", current, value)))
    ctx.register_entity_initializer("Person", lambda current, value: calls.append(("Person", current, value)))
    second = {}
    assert ctx.initialize_entity("Person", second) is second
    assert calls == [("*", ctx, second), ("Person", ctx, second)]
    assert ctx.managed_entities() == [entity, second]


def test_initialize_entity_rejects_invalid_contracts():
    ctx = UserContext()
    with pytest.raises(ValueError):
        ctx.initialize_entity(" ", {})
    with pytest.raises(ValueError):
        ctx.initialize_entity("Person", None)

    with pytest.raises(ValueError):
        ctx.register_entity_initializer("Person", object())
