"""Original loaded scalars owned by runtime, not serialized entity state."""
from copy import deepcopy
from weakref import WeakKeyDictionary


class LoadedScalarSnapshots:
    _values = WeakKeyDictionary()

    @classmethod
    def capture(cls, entity, values):
        cls._values[entity] = deepcopy(values)

    @classmethod
    def values(cls, entity):
        return deepcopy(cls._values.get(entity, {}))

    @classmethod
    def restore(cls, entity, values):
        cls.capture(entity, values)
